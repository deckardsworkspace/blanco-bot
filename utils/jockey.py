"""
Music player class for Blanco. Subclass of mafic.Player.
"""

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from random import shuffle
from time import time
from typing import TYPE_CHECKING, Deque, List, Optional, Tuple

from mafic import Player, PlayerNotConnected
from nextcord import (Colour, Forbidden, HTTPException, Message, NotFound,
                      StageChannel, VoiceChannel)

from views.now_playing import NowPlayingView

from .exceptions import (EndOfQueueError, JockeyError, JockeyException,
                         LavalinkSearchError, SpotifyNoResultsError)
from .jockey_helpers import CustomEmbed, create_error_embed, parse_query
from .lavalink_client import get_deezer_track, get_youtube_matches
from .time_util import human_readable_time

if TYPE_CHECKING:
    from mafic import Track
    from nextcord import Embed
    from nextcord.abc import Connectable, Messageable

    from dataclass.queue_item import QueueItem

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
        self._db = client.database
        client.database.init_guild(channel.guild.id)

        # Queue
        self._queue: Deque['QueueItem'] = deque()
        self._queue_i = -1

        # Repeat
        self._loop = client.database.get_loop(channel.guild.id)
        self._loop_whole = False

        # Shuffle indices
        self._shuffle_indices = []

        # Volume
        self._volume = client.database.get_volume(channel.guild.id)

        # Scrobble executor
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Logger
        self._logger = client.jockey_logger
        self._logger.info(
            'Using node `%s\' for %s',
            self.node.label,
            channel.guild.name
        )

    @property
    def current_index(self) -> int:
        """
        Returns the index of the current track in the queue.
        """
        return self._queue_i

    @property
    def is_looping(self) -> bool:
        """
        Returns whether the player is looping the current track.
        """
        return self._loop

    @is_looping.setter
    def is_looping(self, value: bool):
        """
        Sets whether the player will loop the current track.
        """
        self._loop = value

    @property
    def is_looping_all(self) -> bool:
        """
        Returns whether the player is looping the entire queue.
        """
        return self._loop_whole

    @is_looping_all.setter
    def is_looping_all(self, value: bool):
        """
        Sets whether the player will loop the entire queue.
        """
        self._loop_whole = value

    @property
    def is_shuffling(self) -> bool:
        """
        Returns whether the player is shuffling the queue.
        """
        return len(self._shuffle_indices) > 0

    @property
    def playing(self) -> bool:
        """
        Returns whether the player is currently playing a track.
        """
        return self.current is not None

    @property
    def queue(self) -> Deque['QueueItem']:
        """
        Returns the player queue.
        """
        return self._queue

    @property
    def queue_size(self) -> int:
        """
        Returns the size of the player queue.
        """
        return len(self._queue)

    @property
    def shuffle_indices(self) -> List[int]:
        """
        Returns the list of shuffle indices.

        Blanco uses a list of indices to keep track of the
        shuffled queue, so that it can be restored later if
        the user chooses to unshuffle.
        """
        return self._shuffle_indices

    @shuffle_indices.setter
    def shuffle_indices(self, value: List[int]):
        """
        Sets the list of shuffle indices.
        """
        self._shuffle_indices = value

    @property
    def status_channel(self) -> 'Messageable':
        """
        Returns the status channel for the player.
        """
        channel = self._bot.get_status_channel(self.guild.id)
        if channel is None:
            raise ValueError('Status channel has not been set')
        return channel

    @property
    def volume(self) -> int:
        """
        Returns the player volume.
        """
        return self._volume

    @volume.setter
    def volume(self, value: int):
        """
        Sets the player volume and saves it to the database.
        """
        self._volume = value
        self._db.set_volume(self.guild.id, value)

    async def _edit_np_controls(self, show_controls: bool = True):
        """
        Edits the now playing message to show or hide controls.
        """
        view = None
        if show_controls:
            view = NowPlayingView(self._bot, self)

        np_msg = await self._get_now_playing()
        if isinstance(np_msg, Message):
            try:
                await np_msg.edit(view=view)
            except (HTTPException, Forbidden) as exc:
                self._logger.warning(
                    'Could not edit now playing message for %s: %s',
                    self.guild.name,
                    exc
                )

    async def _enqueue(self, index: int, auto: bool = True) -> bool:
        """
        Attempt to enqueue a track, for use with the skip() method.

        :param index: The index of the track to enqueue.
        :param auto: Whether this is an automatic enqueue, i.e. not part of a user's command.
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
                    'Attempted to skip while disconnected'
                ))
            return False
        except Exception as exc: # pylint: disable=broad-exception-caught
            self._logger.error('Failed to play next track: %s', exc)
            if auto:
                await self.status_channel.send(embed=create_error_embed(
                    f'Unable to play next track: {exc}'
                ))

            # Restore current index
            self._queue_i = current
            return False

        # Scrobble if possible
        await self._scrobble(self._queue[current])

        return result

    async def _get_now_playing(self) -> Optional[Message]:
        np_msg_id = self._db.get_now_playing(self.guild.id)
        if np_msg_id != -1:
            try:
                np_msg = await self.status_channel.fetch_message(np_msg_id)
                return np_msg
            except (Forbidden, HTTPException, NotFound) as exc:
                self._logger.warning(
                    'Failed to fetch now playing message for %s: %s',
                    self.guild.name,
                    exc
                )

        return None

    async def _play(self, item: 'QueueItem') -> bool:
        results = []

        if item.lavalink_track is None:
            # Use ISRC if present
            if item.isrc is not None:
                # Try to match ISRC on Deezer if enabled
                assert self._bot.config is not None
                if self._bot.config.lavalink_nodes[self.node.label].deezer:
                    try:
                        result = await get_deezer_track(self.node, item.isrc)
                    except LavalinkSearchError:
                        self._logger.warning(
                            'No Deezer match for ISRC %s `%s\'',
                            item.isrc,
                            item.title
                        )
                    else:
                        results.append(result)
                        self._logger.debug(
                            'Matched ISRC %s `%s\' on Deezer',
                            item.isrc,
                            item.title
                        )

                # Try to match ISRC on YouTube
                if len(results) == 0:
                    try:
                        results = await get_youtube_matches(
                            self.node,
                            f'"{item.isrc}"',
                            desired_duration_ms=item.duration
                        )
                    except LavalinkSearchError:
                        self._logger.warning(
                            'No YouTube match for ISRC %s `%s\'',
                            item.isrc,
                            item.title
                        )
                    else:
                        self._logger.debug(
                            'Matched ISRC %s `%s\' on YouTube',
                            item.isrc,
                            item.title
                        )

            # Fallback to metadata search
            if len(results) == 0:
                self._logger.error(
                    'No ISRC match for `%s\'. Falling back to metadata search.',
                    item.title
                )
                item.is_imperfect = True

                try:
                    results = await get_youtube_matches(
                        self.node,
                        f'{item.title} {item.artist}',
                        desired_duration_ms=item.duration
                    )
                except LavalinkSearchError as err:
                    self._logger.critical('Failed to play `%s\'.', item.title)
                    self._logger.error(err.message)
                    return False
                else:
                    self._logger.warning(
                        'Using YouTube result `%s\' (%s) for `%s\'',
                        results[0].lavalink_track.title,
                        results[0].lavalink_track.identifier,
                        item.title
                    )

            # Save Lavalink result
            item.lavalink_track = results[0].lavalink_track

        # Play track
        await self.play(item.lavalink_track)

        # We don't want to play if the player is not idle
        # as that will effectively skip the current track.
        if not self.playing:
            await self.resume()

        # Save start time for scrobbling
        item.start_time = int(time())

        return True

    async def _scrobble(self, item: 'QueueItem'):
        if not isinstance(self.channel, VoiceChannel):
            return

        # Check if scrobbling is enabled
        assert self._bot.config is not None
        if not self._bot.config.lastfm_api_key or not self._bot.config.lastfm_shared_secret:
            return

        # Check if track can be scrobbled
        time_now = int(time())
        try:
            duration = item.duration
            if item.lavalink_track is not None:
                duration = item.lavalink_track.length

            if item.start_time is not None and duration is not None:
                # Check if track is longer than 30 seconds
                if duration < 30000:
                    raise ValueError('Track is too short')

                # Check if enough time has passed (1/2 duration or 4 min, whichever is less)
                elapsed_ms = (time_now - item.start_time) * 1000
                if elapsed_ms < min(duration // 2, 240000):
                    raise ValueError('Not enough time has passed')
            else:
                # Default to current time for timestamp
                item.start_time = time_now
        except ValueError as err:
            self._logger.warning('Failed to scrobble `%s\': %s', item.title, err.args[0])

        # Scrobble for every user
        scrobbled = 0
        for member in self.channel.members:
            if not member.bot:
                scrobbler = self._bot.get_scrobbler(member.id)
                if scrobbler is not None:
                    await self._bot.loop.run_in_executor(self._executor, scrobbler.scrobble, item)
                    scrobbled += 1

        self._logger.debug('Scrobbled `%s\' for %d users', item.title, scrobbled)

    async def disconnect(self, *, force: bool = False):
        """
        Removes the controls from Now Playing, then disconnects.
        """
        # Get now playing message
        np_msg = await self._get_now_playing()
        if np_msg is not None:
            try:
                await np_msg.edit(view=None)
            except (HTTPException, Forbidden):
                self._logger.warning(
                    'Failed to remove now playing message for %s',
                    self.guild.name
                )

        # Disconnect
        await super().disconnect(force=force)

    def now_playing(self, current: Optional['Track'] = None) -> 'Embed':
        """
        Returns information about the currently playing track.

        :return: An instance of nextcord.Embed
        """
        if current is None:
            if self.current is None:
                raise EndOfQueueError('No track is currently playing')
            current = self.current

        # Construct Spotify URL if it exists
        track = self._queue[self._queue_i]
        uri = current.uri
        if track.spotify_id is not None:
            uri = f'https://open.spotify.com/track/{track.spotify_id}'

        # Get track duration
        duration_ms = track.duration
        if track.lavalink_track is not None:
            duration_ms = track.lavalink_track.length

        # Build track duration string
        duration = ''
        if isinstance(duration_ms, int):
            h, m, s = human_readable_time(duration_ms) # pylint: disable=invalid-name
            if s > 0:
                duration = f'{s} sec'
            if m > 0:
                duration = f'{m} min {duration}'
            if h > 0:
                duration = f'{h} hr {duration}'

        is_stream = False
        if track.lavalink_track is not None:
            is_stream = track.lavalink_track.stream

        imperfect_msg = ':warning: Playing the [**closest match**]({})'
        embed = CustomEmbed(
            title='Now streaming' if is_stream else 'Now playing',
            description=[
                f'[**{track.title}**]({uri})',
                f'{track.artist}',
                duration if not is_stream else '',
                f'\nrequested by <@{track.requester}>',
                imperfect_msg.format(current.uri) if track.is_imperfect else ''
            ],
            footer=f'Track {self.current_index + 1} of {len(self._queue)}',
            color=Colour.teal(),
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
        except JockeyException:
            raise
        except SpotifyNoResultsError as err:
            raise JockeyError(err.args[0]) from err
        except Exception as exc:
            if self.playing:
                raise JockeyException(str(exc)) from exc
            raise JockeyError(str(exc)) from exc

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

                raise JockeyError(f'Failed to enqueue "{first.title}"\n{enqueue_result}')

        # Send embed
        return first_name if len(new_tracks) == 1 else f'{len(new_tracks)} item(s)'

    async def remove(self, index: int) -> Tuple[str | None, str | None]:
        """
        Removes a track from the queue.
        """
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
            self._shuffle_indices = [
                i - 1
                if i > actual_index else i
                for i in self._shuffle_indices
            ]

        # Adjust current index
        if self._queue_i > actual_index:
            self._queue_i -= 1

        # Return removed track details
        return removed_track.title, removed_track.artist

    async def set_volume(self, volume: int, /):
        """
        Sets the player volume.
        """
        await super().set_volume(volume)
        self.volume = volume

    async def shuffle(self):
        """
        Generates a random permutation of the queue indices for shuffling.
        """
        if len(self._queue) == 0:
            raise EndOfQueueError('Queue is empty, nothing to shuffle')

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
        await self._edit_np_controls(show_controls=False)

        # If index is specified, use that instead
        if index != -1:
            if not await self._enqueue(index, auto=auto):
                await self._edit_np_controls(show_controls=True)
            return

        # Is this autoskipping?
        if auto:
            # Check if we're looping the current track
            if self.is_looping:
                # Re-enqueue the current track
                await self._enqueue(self._queue_i, auto=auto)
                return

        # Set initial index
        next_i = self._shuffle_indices.index(self._queue_i) if self.is_shuffling else self._queue_i
        while 0 <= next_i < self.queue_size:
            # Have we reached an end of the queue?
            if (next_i == self.queue_size - 1 and forward) or (
                next_i == 0 and not forward):
                # Reached an end of the queue, are we looping?
                if self.is_looping_all:
                    next_i = 0 if forward else self.queue_size - 1
                else:
                    if not auto:
                        # If we reached this point,
                        # we are at one of either ends of the queue,
                        # and the user was expecting to skip past it.
                        await self._edit_np_controls(show_controls=True)
                        if forward:
                            raise EndOfQueueError('Reached the end of the queue')
                        raise EndOfQueueError('Reached the beginning of the queue')

                    # Queue likely finished on its own. Scrobble last track.
                    await self._scrobble(self._queue[self._queue_i])
                    return
            else:
                next_i += 1 if forward else -1

            # Try to enqueue the next track
            if not await self._enqueue(next_i, auto=auto):
                await self._edit_np_controls(show_controls=True)
            else:
                return
