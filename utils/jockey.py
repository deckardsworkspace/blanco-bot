from collections import deque
from dataclass.custom_embed import CustomEmbed
from lavalink.events import *
from lavalink.models import DefaultPlayer
from nextcord import Interaction
from nextcord.abc import Messageable
from typing import Optional
from .database import Database
from .exceptions import EndOfQueueError
from .jockey_helpers import *
from .lavalink import LavalinkVoiceClient
from .lavalink_bot import LavalinkBot
from .lavalink_helpers import EventWithPlayer, lavalink_enqueue
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
        self._queue = deque()
        self._current = -1

        # Shuffle indices
        self._shuffle_indices = []

        print(f'Created jockey for guild {guild}')
    
    @property
    def is_connected(self) -> bool:
        return self._player.is_connected
    
    @property
    def is_looping_all(self) -> bool:
        return self._player.repeat
    
    @property
    def is_playing(self) -> bool:
        return self._player is not None and (self._player.is_playing or self._player.paused)
    
    @property
    def is_shuffling(self) -> bool:
        return len(self._shuffle_indices) > 0

    async def destroy(self) -> Messageable:
        # Disconnect Lavalink
        await self._player.stop()

        # Disconnect from the voice channel
        vc = self._bot.get_guild(self._guild).voice_client
        if hasattr(vc, 'disconnect'):
            await vc.disconnect(force=True)
        await self._bot.lavalink.player_manager.destroy(self._guild)

        # Return channel for sending disconnection message
        return self._channel
    
    async def handle_event(self, event: EventWithPlayer):
        """
        Handle an event from the Lavalink player.
        """
        if isinstance(event, TrackStartEvent):
            # Send now playing embed
            embed = create_now_playing_embed(self._player.current)
            await self._channel.send(embed=embed)
        elif isinstance(event, QueueEndEvent):
            # Play next track in queue
            await self.skip()
    
    async def play(self, itx: Interaction, query: str):
        # Get results for query
        new_tracks = await parse_query(itx, self._spotify, query)
        if len(new_tracks):
            # Connect to voice
            if not self.is_connected:
                # Are we connected according to Discord?
                for client in self._bot.voice_clients:
                    if client.guild.id == self._guild:
                        # Remove old connection
                        await client.disconnect()
                await itx.user.voice.channel.connect(cls=LavalinkVoiceClient)

            # Add new tracks to queue
            old_size = len(self._queue)
            self._queue.extend(new_tracks)

            # Are we beginning a new queue?
            first = new_tracks[0]
            first_name = f'**{first.title}**\nby {first.artist}' if first.title is not None else query
            if not self.is_playing:
                # We are! Play the first track.
                self._current = 0
                if not await lavalink_enqueue(self._player, new_tracks[0]):
                    # Failed to enqueue
                    self._queue.clear()
                    self._current = -1
                    return await itx.followup.send(embed=create_error_embed(f'Failed to enqueue {first_name}'))
            else:
                # We are already playing from a queue.
                # Update shuffle indices if applicable.
                if self.is_shuffling:
                    # Append new indices to the end of the list
                    new_indices = [old_size + i for i in range(len(new_tracks))]
                    self._shuffle_indices.extend(new_indices)

            # Send embed
            item_name = first_name if len(new_tracks) == 1 else f'{len(new_tracks)} item(s)'
            await itx.followup.send(embed=create_success_embed(f'Added {item_name} to queue'))

    async def skip(self, itx: Optional[Interaction] = None, forward: bool = True):
        # Queue up the next valid track, if any
        if isinstance(self._current, int):
            # Set initial index
            queue_size = len(self._queue)
            next_i = self._shuffle_indices.index(self._current) if self.is_shuffling else self._current
            while next_i < queue_size:
                # Have we reached the end of the queue?
                if next_i == queue_size - 1:
                    # Reached the end of the queue, are we looping?
                    if self.is_looping_all:
                        embed = CustomEmbed(
                            color=Color.dark_green(),
                            title=f':repeat:｜Looping back to the start',
                            description=[
                                'Reached the end of the queue.',
                                f'Use the `loop all` command to disable.'
                            ]
                        )
                        if itx is not None:
                            await itx.followup.send(embed=embed.get())
                        else:
                            await self._channel.send(embed=embed.get())
                        next_i = 0
                    else:
                        # We are not looping
                        break
                else:
                    next_i += 1 if forward else -1

                # Try playing the track
                track_index = self._shuffle_indices[next_i] if self.is_shuffling else next_i
                track = self._queue[track_index]
                try:
                    if await lavalink_enqueue(self._player, track):
                        if itx is not None:
                            await self._player.skip()

                        # Save new queue index
                        self._current = next_i
                        await itx.followup.send(embed=create_success_embed('Skipped to next track'))
                        return
                except Exception as e:
                    embed = create_error_embed(f'Unable to play track: {track}. Reason: {e}')
                    if itx is not None:
                        await itx.followup.send(embed=embed)
                    else:
                        await self._channel.send(embed=embed)

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
