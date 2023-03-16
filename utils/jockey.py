from collections import deque
from dataclass.custom_embed import CustomEmbed
from dataclass.queue_item import QueueItem
from lavalink.events import *
from lavalink.models import DefaultPlayer
from nextcord import Color, Interaction
from nextcord.abc import Messageable
from random import shuffle
from typing import Deque, Optional, Union
from views.now_playing import NowPlayingView
from .database import Database
from .exceptions import EndOfQueueError
from .jockey_helpers import *
from .lavalink_voice import EventWithPlayer, LavalinkVoiceClient
from .lavalink_bot import LavalinkBot
from .paginator import Paginator
from .spotify_client import Spotify


class Jockey:
    """
    Class that handles music playback for a single guild.
    Contains all the methods for music playback, along with a
    local instance of an in-memory database for fast queueing.
    """

    def __init__(self, guild: int, db: Database, bot: LavalinkBot, player: DefaultPlayer, spotify: Spotify, channel: Messageable):
        self._bot = bot
        self._guild = guild
        self._spotify = spotify
        self._channel = channel

        # Database
        self._db = db
        self._db.init_guild(guild)

        # Player instance
        self._player = player
        manual_await(player.set_volume(db.get_volume(guild)))
        player.set_repeat(db.get_loop(guild))

        # Queue
        self._queue: Deque[QueueItem] = deque()
        self._current = -1
        self._loop_whole = False

        # Shuffle indices
        self._shuffle_indices = []

        print(f'Created jockey for guild {guild} (bound to node "{player.node.name}")')
    
    @property
    def current_index(self) -> int:
        return self._current

    @property
    def is_connected(self) -> bool:
        return self._player.is_connected
    
    @property
    def is_looping(self) -> bool:
        return self._player.repeat
    
    @property
    def is_looping_all(self) -> bool:
        return self._loop_whole
    
    @is_looping_all.setter
    def is_looping_all(self, value: bool):
        self._loop_whole = value
    
    @property
    def is_paused(self) -> bool:
        return self._player.paused
    
    @property
    def is_playing(self) -> bool:
        return self._player is not None and (self._player.is_playing or self._player.paused)
    
    @property
    def is_shuffling(self) -> bool:
        return len(self._shuffle_indices) > 0
    
    @property
    def queue_size(self) -> int:
        return len(self._queue)
    
    @property
    def volume(self) -> int:
        return self._player.volume
    
    async def _disconnect(self):
        # Disconnect Lavalink
        await self._player.stop()

        # Disconnect from the voice channel
        vc = self._bot.get_guild(self._guild).voice_client
        if hasattr(vc, 'disconnect'):
            await vc.disconnect(force=True)
        await self._bot.lavalink.player_manager.destroy(self._guild)
    
    async def _enqueue(self, query: QueueItem) -> Optional[str]:
        if query.lavalink_track is not None:
            # Track has already been processed by Lavalink so just play it directly
            self._player.add(requester=query.requester, track=query.lavalink_track)
        else:
            # Use ISRC if present
            results = []
            if query.isrc is not None:
                try:
                    results = await get_youtube_matches(self._player, f'"{query.isrc}"', desired_duration_ms=query.duration)
                except LavalinkSearchError:
                    query.is_imperfect = True
                    pass
            
            # Fallback to metadata search
            if not len(results):
                try:
                    results = await get_youtube_matches(self._player, f'{query.title} {query.artist}', desired_duration_ms=query.duration)
                except Exception as e:
                    return str(e)

            # Try to add first result directly to Lavalink queue
            self._player.add(requester=query.requester, track=results[0].lavalink_track)

        # We don't want to call .play() if the player is not idle
        # as that will effectively skip the current track.
        if not self.is_playing:
            await self._player.play()

        return None

    async def _try_enqueue(self, itx: Optional[Interaction], index: int) -> bool:
        track_index = self._shuffle_indices[index] if self.is_shuffling else index
        track = self._queue[track_index]
        try:
            # Save current index in case enqueue fails
            current = self._current
            self._current = track_index

            if await self._enqueue(track) is None:
                if itx is not None:
                    await self._player.skip()
                    await itx.followup.send(embed=create_success_embed(f'Skipped'), delete_after=5)
        except Exception as e:
            embed = create_error_embed(f'Unable to play track {index}. Reason: {e}')
            if itx is not None:
                await itx.followup.send(embed=embed)
            else:
                await self._channel.send(embed=embed)
            
            # Restore current index
            self._current = current
            
            # Restore now playing message controls
            await self.now_playing(itx.channel)
            return False
        else:
            return True

    async def destroy(self) -> Messageable:
        # Disconnect from voice
        await self._disconnect()

        # Remove view from now playing message
        last_msg_id = self._db.get_now_playing(self._guild)
        if last_msg_id != -1:
            try:
                last_msg = await self._channel.fetch_message(last_msg_id)
                await last_msg.edit(view=None)
            except:
                pass

        # Return channel for sending disconnection message
        return self._channel
    
    async def display_queue(self, itx: Interaction):
        if len(self._queue) == 0:
            await itx.followup.send(embed=create_error_embed('Queue is empty'))
            return
        
        # Show loop status
        embed_header = [f'{len(self._queue)} total']
        if self.is_looping_all:
            embed_header.append(':repeat: Looping entire queue (`/unloopall` to disable)')
        
        # Show shuffle status
        queue = list(self._queue)
        current = self._current
        if self.is_shuffling:
            embed_header.append(':twisted_rightwards_arrows: Shuffling queue  (`/unshuffle` to disable)')
            current = self._shuffle_indices.index(current)

            # Get shuffled version of queue
            queue = [self._queue[i] for i in self._shuffle_indices]

        # Show queue in chunks of 10 per page
        pages = []
        homepage = 0
        count = 1
        prefix_len = len(str(len(self._queue)))
        for i, chunk in enumerate(list_chunks(queue)):
            chunk_tracks = []

            # Create page content
            track: QueueItem
            for track in chunk:
                title, artist = track.get_details()

                # Pad index with spaces if necessary
                index = str(count)
                while len(index) < prefix_len:
                    index = ' ' + index
                
                # Is this the current track?
                line_prefix = '  '
                if count - 1 == current:
                    line_prefix = '> '
                    homepage = i
                
                # Create item line
                line_prefix = '> ' if count - 1 == current else '  '
                line = f'{line_prefix} {index} :: {title} - {artist}'

                # Truncate line if necessary
                if len(line) > 50:
                    line = line[:50] + '...'
                else:
                    line = f'{line:50.50}'
                chunk_tracks.append(line)
                count += 1

            # Create page
            tracks = '\n'.join(chunk_tracks)
            embed_body = embed_header + [f'```asciidoc\n{tracks}```']
            embed = CustomEmbed(
                title=f'Queue for {self._bot.get_guild(self._guild).name}',
                description='\n'.join(embed_body),
                color=Color.lighter_gray()
            )
            pages.append(embed.get())
    
        # Run paginator
        paginator = Paginator(itx)
        return await paginator.run(pages, start=homepage)

    async def handle_event(self, event: EventWithPlayer):
        """
        Handle an event from the Lavalink player.
        """
        if isinstance(event, TrackStartEvent):
            # Send now playing embed
            await self.now_playing(self._channel)
        elif isinstance(event, QueueEndEvent):
            # Play next track in queue
            await self.skip()
    
    async def loop(self, itx: Interaction, whole_queue: bool = False):
        if whole_queue:
            if not self.is_looping_all:
                self.is_looping_all = True
                return await itx.response.send_message(embed=create_success_embed('Looping entire queue'))
            else:
                return await itx.response.send_message(embed=create_success_embed('Already looping entire queue'))
        else:
            if not self.is_looping:
                self._player.set_repeat(repeat=True)
                return await itx.response.send_message(embed=create_success_embed('Looping current track'))
            else:
                return await itx.response.send_message(embed=create_success_embed('Already looping current track'))
    
    async def now_playing(self, recipient: Union[Interaction, Messageable]):
        # Delete last now playing message, if it exists
        last_msg_id = self._db.get_now_playing(self._guild)
        if last_msg_id != -1:
            try:
                last_msg = await self._channel.fetch_message(last_msg_id)
                await last_msg.delete()
            except:
                pass

        # Send now playing embed
        real_uri = ''
        if self._player.current is not None:
            real_uri = self._player.current.uri
        embed = create_now_playing_embed(self._queue[self._current], real_uri)
        view = NowPlayingView(self._bot, self._player)
        if isinstance(recipient, Interaction):
            if await self._bot.is_owner(recipient.user):
                embed.set_footer(text=f'Connected to node `{self._player.node.name}`')
            message = await recipient.followup.send(embed=embed, view=view)
        else:
            message = await recipient.send(embed=embed, view=view)

        # Save now playing message ID
        self._db.set_now_playing(self._guild, message.id)

    async def pause(self, itx: Interaction):
        if not self.is_paused:
            await self._player.set_pause(pause=True)
            await itx.followup.send(embed=create_success_embed('Paused'), delete_after=5)
        else:
            await itx.followup.send(embed=create_error_embed('Nothing to pause'))
    
    async def play(self, itx: Interaction, query: str):
        # Connect to voice
        if not self.is_connected:
            # Are we connected according to Discord?
            for client in self._bot.voice_clients:
                if client.guild.id == self._guild:
                    # Remove old connection
                    await client.disconnect()
            
            # Check if we have permission to connect to voice
            vc = itx.user.voice.channel
            if not vc:
                return await itx.followup.send(embed=create_error_embed('You are not in a voice channel'))
            elif not vc.permissions_for(itx.guild.me).connect:
                return await itx.followup.send(embed=create_error_embed(f'I do not have permission to connect to <#{vc.id}>'))
            await vc.connect(cls=LavalinkVoiceClient)

        # Get results for query
        new_tracks = await parse_query(itx, self._player, self._spotify, query)
        if not len(new_tracks):
            # Disconnect from voice
            await self._disconnect()

        # Add new tracks to queue
        old_size = len(self._queue)
        self._queue.extend(new_tracks)

        # Update shuffle indices if applicable
        if self.is_shuffling:
            new_indices = [old_size + i for i in range(len(new_tracks))]
            self._shuffle_indices.extend(new_indices)

        # Are we beginning a new queue?
        first = new_tracks[0]
        first_name = f'**{first.title}**\n{first.artist}' if first.title is not None else query
        if not self.is_playing:
            # We are! Play the first track.
            current = self._current
            self._current = old_size
            enqueue_result = await self._enqueue(new_tracks[0])
            if enqueue_result is not None:
                # Failed to enqueue, restore state
                for _ in range(old_size, len(self._queue)):
                    del self._queue[-1]
                self._current = current
                if self.is_shuffling:
                    self._shuffle_indices = self._shuffle_indices[:old_size]

                return await itx.followup.send(embed=create_error_embed(f'Failed to enqueue "{first.title}"\n{enqueue_result}'))

        # Send embed
        item_name = first_name if len(new_tracks) == 1 else f'{len(new_tracks)} item(s)'
        await itx.followup.send(embed=create_success_embed(
            title='Added to queue',
            body=item_name
        ))
    
    async def remove(self, itx: Interaction, index: int):
        # Translate index if shuffling
        actual_index = index
        if self.is_shuffling:
            actual_index = self._shuffle_indices[index]

        # Remove track from queue
        removed_track = self._queue[actual_index]
        del self._queue[actual_index]
        if self.is_shuffling:
            del self._shuffle_indices[index]
        
            # Decrement future shuffle indices by 1
            self._shuffle_indices = [i - 1 if i > actual_index else i for i in self._shuffle_indices]
        
        # Adjust current index
        if self._current > actual_index:
            self._current -= 1
        
        # Send embed
        await itx.followup.send(embed=create_success_embed(
            title='Removed from queue',
            body=f'**{removed_track.title}**\n{removed_track.artist}'
        ))
    
    async def set_volume(self, itx: Interaction, level: int):
        # Set new volume
        await self._player.set_volume(level)

        # Save new volume to database
        self._db.set_volume(self._guild, level)

        # Send response
        await itx.followup.send(embed=create_success_embed(f'Volume set to {level}'))

    async def shuffle(self, itx: Interaction):
        if not len(self._queue):
            return await itx.followup.send(embed=create_error_embed('Queue is empty, nothing to shuffle'))
        
        # Are we already shuffling?
        action = 'reshuffled' if self.is_shuffling else 'shuffled'

        # Shuffle indices
        indices = [i for i in range(len(self._queue)) if i != self._current]
        shuffle(indices)

        # Put current track at the start of the list
        indices.insert(0, self._current)

        # Save shuffled indices
        self._shuffle_indices = indices

        # Send reply
        return await itx.followup.send(embed=create_success_embed(f'{len(self._queue)} tracks {action}'))

    async def skip(self, itx: Optional[Interaction] = None, forward: bool = True, index: int = -1):
        # It takes a while for the player to skip, so let's remove the player controls
        # while we wait to prevent the user from spamming them.
        np_msg = self._db.get_now_playing(self._guild)
        if np_msg != -1:
            try:
                np_msg = await self._channel.fetch_message(np_msg)
                await np_msg.edit(view=None)
            except:
                pass

        # If index is specified, use that instead
        if index != -1:
            if await self._try_enqueue(itx, index):
                return
        else:
            # Queue up the next valid track, if any
            if isinstance(self._current, int):
                # Set initial index
                queue_size = len(self._queue)
                next_i = self._shuffle_indices.index(self._current) if self.is_shuffling else self._current
                while next_i < queue_size:
                    # Have we reached the end of the queue?
                    if next_i == queue_size - 1 and forward:
                        # Reached the end of the queue, are we looping?
                        if self.is_looping_all:
                            embed = CustomEmbed(
                                color=Color.dark_green(),
                                title=f':repeat:｜Looping back to the start',
                                description=[
                                    'Reached the end of the queue.',
                                    f'Use the `/unloopall` command to disable.'
                                ]
                            )
                            if itx is not None:
                                await itx.followup.send(embed=embed.get(), delete_after=5)
                            else:
                                await self._channel.send(embed=embed.get(), delete_after=5)
                            next_i = 0
                        else:
                            # If we reached this point, we are at one of either ends of the queue,
                            # and the user was expecting to skip to the next.
                            if itx is not None:
                                if forward:
                                    # Have PlayerCog disconnect us from voice.
                                    await itx.followup.send(embed=create_success_embed('Skipped to the end'))
                                    raise EndOfQueueError
                                else:
                                    embed = create_error_embed('Reached the start of the queue.')
                                    await itx.followup.send(embed=embed)
                            return
                    else:
                        next_i += 1 if forward else -1
                    
                    # Try to enqueue the next track
                    if await self._try_enqueue(itx, next_i):
                        return
    
    async def unloop(self, itx: Interaction, whole_queue: bool = False):
        if whole_queue:
            if self.is_looping_all:
                self.is_looping_all = False
                return await itx.response.send_message(embed=create_success_embed('Stopped looping entire queue'))
            else:
                return await itx.response.send_message(embed=create_success_embed('Not currently looping entire queue'))
        else:
            if self.is_looping:
                self._player.set_repeat(repeat=False)
                return await itx.response.send_message(embed=create_success_embed('Stopped looping current track'))
            else:
                return await itx.response.send_message(embed=create_success_embed('Not currently looping current track'))
    
    async def unpause(self, itx: Interaction):
        if self.is_paused:
            await self._player.set_pause(pause=False)
            await itx.followup.send(embed=create_success_embed('Resumed'), delete_after=5)
        else:
            await itx.followup.send(embed=create_error_embed('Nothing to resume'))
    
    async def unshuffle(self, itx: Interaction):
        if self.is_shuffling:
            self._shuffle_indices = []
            await itx.followup.send(embed=create_success_embed('Unshuffled'))
        else:
            await itx.followup.send(embed=create_error_embed('Current queue is not shuffled'))
