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
    if query.lavalink_track is not None:
        # Track has already been processed by Lavalink so just play it directly
        player.add(requester=query.requester, track=query.lavalink_track)
    else:
        # Get the results for the query from Lavalink
        results = await lavalink_search(player, query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # Alternatively, results['tracks'] could be an empty array if the query yielded no tracks.
        if not results or not results['tracks']:
            return False

        # Try to add track directly to Lavalink queue
        if results['loadType'] == 'SEARCH_RESULT' or results['loadType'] == 'TRACK_LOADED':
            track = AudioTrack(results['tracks'][0], query.requester)
            player.add(requester=query.requester, track=track)
        else:
            return False

    # We don't want to call .play() if the player is not idle
    # as that will effectively skip the current track.
    if not player.is_playing and not player.paused:
        await player.play()

    return True
