from dataclass.custom_embed import CustomEmbed
from dataclass.queue_item import QueueItem
from itertools import islice
from mafic import SearchType
from nextcord import Color, Embed
from typing import Any, Generator, List, Optional, TYPE_CHECKING
from .exceptions import *
from .lavalink_client import *
from .spotify_client import Spotify
from .url import *
if TYPE_CHECKING:
    from dataclass.spotify_track import SpotifyTrack
    from mafic import Node


def create_error_embed(message: str) -> Embed:
    embed = CustomEmbed(
        color=Color.red(),
        title=':x:｜Error processing command',
        description=message
    )
    return embed.get()


def create_success_embed(title: Optional[str] = None, body: Optional[str] = None) -> Embed:
    if body is None:
        if title is None:
            raise ValueError('Either title or body must be specified')

        body = title
        title = 'Success'
    
    embed = CustomEmbed(
        color=Color.green(),
        title=f':white_check_mark:｜{title}',
        description=body
    )
    return embed.get()


def list_chunks(data: List[Any]) -> Generator[List[Any], Any, Any]:
    for i in range(0, len(data), 10):
        yield list(islice(data, i, i + 10))


async def parse_query(node: 'Node', spotify: Spotify, query: str, requester: int) -> List[QueueItem]:
    query_is_url = check_url(query)
    if query_is_url:
        if check_spotify_url(query):
            # Query is a Spotify URL.
            return await parse_spotify_query(spotify, query, requester)
        elif check_youtube_url(query) or check_ytmusic_url(query):
            # Query is a YouTube URL.
            return await parse_youtube_query(node, query, requester)
        elif check_youtube_playlist_url(query) or check_ytmusic_playlist_url(query):
            # Query is a YouTube playlist URL.
            return await parse_youtube_playlist(node, query, requester)
        elif check_sc_url(query):
            # Query is a SoundCloud URL.
            return await parse_sc_query(node, query, requester)
    
        # Direct URL playback is deprecated
        raise JockeyDeprecatedError('Direct playback from unsupported URLs is deprecated')
    
    # Attempt to look for a matching track on Spotify
    yt_query = query
    try:
        results = spotify.search(query, limit=10)
    except SpotifyNoResultsError:
        pass
    else:
        # Rank results by similarity to query
        similarities = [
            check_similarity(query, f'{result.title} {result.artist}')
            for result in results
        ]

        # Check if the top result is similar enough
        top_similarity = max(similarities)
        if top_similarity > 0.6:
            # Return
            track = results[similarities.index(top_similarity)]
            return [QueueItem(
                requester=requester,
                title=track.title,
                artist=track.artist,
                spotify_id=track.spotify_id,
                duration=track.duration_ms,
                artwork=track.artwork,
                isrc=track.isrc
            )]

    # Play the first matching track on YouTube
    results = await get_youtube_matches(node, yt_query, automatic=False)
    result = results[0]
    return [QueueItem(
        title=result.title,
        artist=result.author,
        artwork=result.artwork_url,
        duration=result.duration_ms,
        requester=requester,
        url=result.url,
        lavalink_track=result.lavalink_track
    )]


async def parse_sc_query(node: 'Node', query: str, requester: int) -> List[QueueItem]:
    # Get entity type
    entity_type = get_sctype_from_url(query)

    try:
        # Get results with Lavalink
        set_name, tracks = await get_tracks(node, query, search_type=SearchType.SOUNDCLOUD.value)
    except:
        raise LavalinkInvalidIdentifierError(f'Entity {query} is private, nonexistent, or has no stream URL')
    else:
        return [QueueItem(
            requester=requester,
            title=track.title,
            artist=track.author,
            artwork=track.artwork_url,
            duration=track.duration_ms,
            url=track.url,
            lavalink_track=track.lavalink_track
        ) for track in tracks]


async def parse_spotify_query(spotify: Spotify, query: str, requester: int) -> List[QueueItem]:
    # Get artwork for Spotify album/playlist
    sp_type, sp_id = get_spinfo_from_url(query, valid_types=['track', 'album', 'playlist'])

    new_tracks = []
    track_queue: List['SpotifyTrack']
    if sp_type == 'track':
        # Get track details from Spotify
        track_queue = [spotify.get_track(sp_id)]
    else:
        # Get playlist or album tracks from Spotify
        track_queue = spotify.get_tracks(sp_type, sp_id)[2]

    if len(track_queue) < 1:
        # No tracks.
        raise SpotifyNoResultsError

    # At least one track.
    for track in track_queue:
        new_tracks.append(QueueItem(
            requester=requester,
            title=track.title,
            artist=track.artist,
            spotify_id=track.spotify_id,
            duration=track.duration_ms,
            artwork=track.artwork,
            isrc=track.isrc
        ))
    
    return new_tracks


async def parse_youtube_playlist(node: 'Node', query: str, requester: int) -> List[QueueItem]:
    try:
        # Get playlist tracks from YouTube
        playlist_id = get_ytlistid_from_url(query)
        _, tracks = await get_tracks(
            node,
            f'https://youtube.com/playlist?list={playlist_id}',
            search_type=SearchType.YOUTUBE.value
        )
    except:
        # No tracks.
        raise LavalinkInvalidIdentifierError(query, f'Playlist is empty, private, or nonexistent')
    else:
        return [QueueItem(
            requester=requester,
            title=track.title,
            artist=track.author,
            artwork=track.artwork_url,
            duration=track.duration_ms,
            url=track.url,
            lavalink_track=track.lavalink_track
        ) for track in tracks]


async def parse_youtube_query(node: 'Node', query: str, requester: int) -> List[QueueItem]:
    # Is it a video?
    try:
        video_id = get_ytid_from_url(query)

        # Get the video's details
        _, video = await get_tracks(node, video_id, search_type=SearchType.YOUTUBE.value)
        return [QueueItem(
            title=video[0].title,
            artist=video[0].author,
            artwork=video[0].artwork_url,
            requester=requester,
            duration=video[0].duration_ms,
            url=video[0].url,
            lavalink_track=video[0].lavalink_track
        )]
    except LavalinkInvalidIdentifierError:
        raise
    except:
        raise LavalinkInvalidIdentifierError(query, 'Only YouTube video and playlist URLs are supported.')
