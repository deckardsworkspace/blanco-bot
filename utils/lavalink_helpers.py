from dataclasses import asdict
from dataclass.queue_item import QueueItem
from lavalink.events import *
from lavalink.models import AudioTrack, DefaultPlayer
from nextcord.ext.commands import Context
from typing import Union
from .jockey_helpers import create_error_embed
from .youtube_client import get_youtube_matches


EventWithPlayer = Union[
    PlayerUpdateEvent,
    QueueEndEvent,
    TrackEndEvent,
    TrackExceptionEvent,
    TrackStuckEvent,
    TrackStartEvent,
    NodeChangedEvent,
    WebSocketClosedEvent
]


async def lavalink_search(player: DefaultPlayer, queue_item: QueueItem):
    if queue_item.url is not None:
        # Tell Lavalink to play the URL directly
        return await player.node.get_tracks(queue_item.url)

    if queue_item.title is not None:
        # If the duration is specified, use it to find the track
        if queue_item.duration > 0:
            results = await get_youtube_matches(f'{queue_item.title} {queue_item.artist}', desired_duration_ms=queue_item.duration)
            return await player.node.get_tracks(results[0].url)
        return await player.node.get_tracks(f'ytsearch:{queue_item.title} {queue_item.artist} audio')
    else:
        raise RuntimeError(f'Cannot process incomplete queue item {asdict(queue_item)}')


async def lavalink_enqueue(player: DefaultPlayer, query: QueueItem) -> bool:
    # Get the results for the query from Lavalink
    results = await lavalink_search(player, query)

    # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
    # Alternatively, results['tracks'] could be an empty array if the query yielded no tracks.
    if not results or not results['tracks']:
        return False

    # Valid loadTypes are:
    #   TRACK_LOADED    - single video/direct URL
    #   PLAYLIST_LOADED - direct URL to playlist
    #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
    #   NO_MATCHES      - query yielded no results
    #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
    if results['loadType'] == 'SEARCH_RESULT' or results['loadType'] == 'TRACK_LOADED':
        track = results['tracks'][0]

        # Save track metadata to player storage
        if hasattr(track, 'identifier'):
            player.store(track['identifier'], track)

            # Add Spotify data to track metadata
            if query.spotify_id is not None:
                player.store(f'{track["identifier"]}-spotify', {
                    'name': query.title,
                    'artist': query.artist,
                    'id': query.spotify_id
                })

        # Add track directly to Lavalink queue
        track = AudioTrack(track, query.requester)
        player.add(requester=query.requester, track=track)

    # We don't want to call .play() if the player is not idle
    # as that will effectively skip the current track.
    if not player.is_playing and not player.paused:
        await player.play()

    return True
