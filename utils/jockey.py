from collections import deque
from mafic import Player, PlayerNotConnected
from nextcord import Message, StageChannel, VoiceChannel
from random import shuffle
from typing import Deque, TYPE_CHECKING
from views.now_playing import NowPlayingView
from .exceptions import *
from .jockey_helpers import *
from .string_util import human_readable_time
if TYPE_CHECKING:
    from dataclass.queue_item import QueueItem
    from nextcord import Embed
    from nextcord.abc import Connectable, Messageable
    from .blanco import BlancoBot


class Jockey(Player['BlancoBot']):
    """
    Class that handles music playback for a single guild.
    Contains all the methods for music playback, along with a
    local instance of an in-memory database for fast queueing.
    """

    def __init__(self, client: 'BlancoBot', channel: 'Connectable'):
        super().__init__(client, channel)
        self._bot = client

        if not isinstance(channel, StageChannel) and not isinstance(channel, VoiceChannel):
            raise TypeError(f'Channel must be a voice channel, not {type(channel)}')

        # Database
        self._db = client.db
        client.db.init_guild(channel.guild.id)

        # Queue
        self._queue: Deque['QueueItem'] = deque()
        self._queue_i = -1

        # Repeat
        self._loop = client.db.get_loop(channel.guild.id)
        self._loop_whole = False

        # Suppress auto-skip on TrackEndEvents when the user skips using command
        # This will be read by the event handler in main.py
        self._suppress_skip = False

        # Shuffle indices
        self._shuffle_indices = []

        # Volume
        self._volume = client.db.get_volume(channel.guild.id)

        print(f'[jockey] Init done for {channel.guild.name}')

    @property
    def current_index(self) -> int:
        return self._queue_i
    
    @property
    def is_looping(self) -> bool:
        return self._loop
    
    @is_looping.setter
    def is_looping(self, value: bool):
        self._loop = value
    
    @property
    def is_looping_all(self) -> bool:
        return self._loop_whole
    
    @is_looping_all.setter
    def is_looping_all(self, value: bool):
        self._loop_whole = value
    
    @property
    def is_shuffling(self) -> bool:
        return len(self._shuffle_indices) > 0

    @property
    def playing(self) -> bool:
        return self.current is not None

    @property
    def queue(self) -> Deque['QueueItem']:
        return self._queue
    
    @property
    def queue_size(self) -> int:
        return len(self._queue)
    
    @property
    def shuffle_indices(self) -> List[int]:
        return self._shuffle_indices
    
    @shuffle_indices.setter
    def shuffle_indices(self, value: List[int]):
        self._shuffle_indices = value
    
    @property
    def suppress_skip(self) -> bool:
        return self._suppress_skip

    @suppress_skip.setter
    def suppress_skip(self, value: bool):
        self._suppress_skip = value
    
    @property
    def status_channel(self) -> 'Messageable':
        channel = self._bot.get_status_channel(self.guild.id)
        if channel is None:
            raise ValueError('Status channel has not been set')
        return channel
    
    @property
    def volume(self) -> int:
        return self._volume
    
    @volume.setter
    def volume(self, value: int):
        self._volume = value
        self._db.set_volume(self.guild.id, value)
    
    async def _enqueue(self, index: int, auto: bool = True) -> bool:
        """
        Attempt to enqueue a track, for use with the skip() method.
        """
        track_index = self._shuffle_indices[index] if self.is_shuffling else index
        track = self._queue[track_index]

        # Save current index in case enqueue fails
        current = self._queue_i
        self._queue_i = track_index
        try:
            result = await self._play(track)
        except PlayerNotConnected:
            if not auto:
                await self.status_channel.send(embed=create_error_embed(
                    f'Attempted to skip while disconnected'
                ))
            return False
        except Exception as e:
            if auto:
                await self.status_channel.send(embed=create_error_embed(
                    f'Unable to play next track: {e}'
                ))
            
            # Restore current index
            self._queue_i = current
            return False
        else:
            return result
    
    async def _play(self, item: QueueItem) -> bool:
        if item.lavalink_track is not None:
            # Track has already been processed by Lavalink so just play it directly
            await self.play(item.lavalink_track)
        else:
            # Use ISRC if present
            results = []
            if item.isrc is not None:
                try:
                    results = await get_youtube_matches(self.node, f'"{item.isrc}"', desired_duration_ms=item.duration)
                except LavalinkSearchError:
                    item.is_imperfect = True
                    pass
            
            # Fallback to metadata search
            if not len(results):
                try:
                    results = await get_youtube_matches(self.node, f'{item.title} {item.artist}', desired_duration_ms=item.duration)
                except LavalinkSearchError as e:
                    print(f'[jockey::_play] Failed to play: {e}')
                    return False

            # Try to add first result directly to Lavalink queue
            await self.play(results[0].lavalink_track)

        # We don't want to play if the player is not idle
        # as that will effectively skip the current track.
        if not self.playing:
            await self.resume()

        return True

    def now_playing(self) -> 'Embed':
        """
        Returns information about the currently playing track.

        :return: An instance of nextcord.Embed
        """
        if self.current is None:
            raise EndOfQueueError('No track is currently playing')
        
        # Construct Spotify URL if it exists
        track = self._queue[self._queue_i]
        uri = self.current.uri
        if track.spotify_id is not None:
            uri = f'https://open.spotify.com/track/{track.spotify_id}'
        
        # Get track duration
        duration = ''
        if isinstance(track.duration, int):
            h, m, s = human_readable_time(track.duration)
            duration = f'{s} sec'
            if m > 0:
                duration = f'{m} min {duration}'
            if h > 0:
                duration = f'{h} hr {duration}'

        is_stream = False
        if track.lavalink_track is not None:
            is_stream = track.lavalink_track.stream
        
        embed = CustomEmbed(
            title='Now streaming' if is_stream else 'Now playing',
            description=[
                f'[**{track.title}**]({uri})',
                f'{track.artist}',
                duration if not is_stream else '',
                f'\nrequested by <@{track.requester}>',
                ':warning: Could not find a perfect match for this track.' if track.is_imperfect else '',
                f'Playing the [closest match]({self.current.uri}) instead.' if track.is_imperfect else ''
            ],
            footer=f'Track {self.current_index + 1} of {len(self._queue)}',
            color=Color.teal(),
            thumbnail_url=track.artwork,
            timestamp_now=True
        )
        return embed.get()

    async def play_impl(self, query: str, requester: int) -> str:
        """
        Adds an item to the player queue and begins playback if necessary.

        :param query: The query to play.
        :param requester: The ID of the user who requested the track.
        :return: A string containing the name of the track that was added.
        """
        # Get results for query
        try:
            new_tracks = await parse_query(
                self.node,
                self._bot.spotify,
                query,
                requester
            )
        except IndexError:
            raise JockeyStartError('No results found for query')
        except LavalinkInvalidIdentifierError as e:
            raise JockeyStartError(f'Invalid identifier: {e}')
        except SpotifyInvalidURLError:
            raise JockeyStartError('Can only play tracks, albums, and playlists from Spotify')
        except SpotifyNoResultsError:
            raise JockeyStartError('No results found for query, or playlist or album is empty')
        except JockeyDeprecatedError:
            # Just bubble this up
            raise
        except Exception as e:
            raise JockeyStartError(f'Error parsing query: {e}')
        
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
        if not self.playing:
            # We are! Play the first track.
            current = self._queue_i
            self._queue_i = old_size
            enqueue_result = await self._play(new_tracks[0])
            if not enqueue_result:
                # Failed to enqueue, restore state
                for _ in range(old_size, len(self._queue)):
                    del self._queue[-1]
                self._queue_i = current
                if self.is_shuffling:
                    self._shuffle_indices = self._shuffle_indices[:old_size]

                raise JockeyStartError(f'Failed to enqueue "{first.title}"\n{enqueue_result}')

        # Send embed
        return first_name if len(new_tracks) == 1 else f'{len(new_tracks)} item(s)'

    async def remove(self, index: int) -> Tuple[str | None, str | None]:
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
        if self._queue_i > actual_index:
            self._queue_i -= 1
        
        # Return removed track details
        return removed_track.title, removed_track.artist

    async def set_volume(self, volume: int):
        await super().set_volume(volume)
        self.volume = volume
    
    async def shuffle(self):
        if not len(self._queue):
            raise EndOfQueueError('Queue is empty, nothing to shuffle')
        
        # Are we already shuffling?
        action = 'reshuffled' if self.is_shuffling else 'shuffled'

        # Shuffle indices
        indices = [i for i in range(len(self._queue)) if i != self._queue_i]
        shuffle(indices)

        # Put current track at the start of the list
        indices.insert(0, self._queue_i)

        # Save shuffled indices
        self._shuffle_indices = indices

    async def skip(self, forward: bool = True, index: int = -1, auto: bool = True):
        """
        Skips the current track and plays the next one in the queue.
        """
        # It takes a while for the player to skip,
        # so let's remove the player controls while we wait
        # to prevent the user from spamming them.
        np_msg = self._db.get_now_playing(self.guild.id)
        if np_msg != -1:
            try:
                np_msg = await self.status_channel.fetch_message(np_msg)
                await np_msg.edit(view=None)
            except:
                pass
        
        # If index is specified, use that instead
        if index != -1:
            # Suppress next autoskip
            self._suppress_skip = True
            
            if not await self._enqueue(index, auto=auto):
                # Restore now playing message controls
                view = NowPlayingView(self._bot, self)
                if isinstance(np_msg, Message):
                    try:
                        await np_msg.edit(view=view)
                    except:
                        pass
            return

        # Is this autoskipping?
        if auto:
            # Check if we're looping the current track
            if self.is_looping:
                # Re-enqueue the current track
                await self._enqueue(self._queue_i, auto=auto)
                return
        else:
            # Suppress next autoskip
            self._suppress_skip = True

        # Queue up the next valid track, if any
        if isinstance(self._queue_i, int):
            # Set initial index
            next_i = self._shuffle_indices.index(self._queue_i) if self.is_shuffling else self._queue_i
            while next_i < self.queue_size:
                # Have we reached the end of the queue?
                if next_i == self.queue_size - 1 and forward:
                    # Reached the end of the queue, are we looping?
                    if self.is_looping_all:
                        next_i = 0
                    else:
                        # If we reached this point,
                        # we are at one of either ends of the queue,
                        # and the user was expecting to skip to the next.
                        if not auto:
                            if forward:
                                raise EndOfQueueError('Reached the end of the queue')
                            raise EndOfQueueError('Reached the start of the queue')
                        return
                else:
                    next_i += 1 if forward else -1
                
                # Try to enqueue the next track
                if await self._enqueue(next_i, auto=auto):
                    return
