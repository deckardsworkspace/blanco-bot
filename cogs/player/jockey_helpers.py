"""
Helper functions for the music player.
"""

from typing import TYPE_CHECKING, List, Tuple, TypeVar

from mafic import SearchType
from spotipy.exceptions import SpotifyException
from thefuzz import fuzz

from dataclass.queue_item import QueueItem
from utils.config import DEBUG_ENABLED
from utils.constants import CONFIDENCE_THRESHOLD
from utils.exceptions import (JockeyException, LavalinkInvalidIdentifierError,
                              LavalinkSearchError, SpotifyNoResultsError)
from utils.logger import create_logger
from utils.spotify_client import Spotify
from utils.url import (check_sc_url, check_spotify_url, check_url,
                       check_youtube_playlist_url, check_youtube_url,
                       check_ytmusic_playlist_url, check_ytmusic_url,
                       get_spinfo_from_url, get_ytid_from_url,
                       get_ytlistid_from_url)

from .lavalink_client import (check_similarity, get_deezer_matches,
                              get_deezer_track, get_soundcloud_matches,
                              get_youtube_matches)

if TYPE_CHECKING:
    from mafic import Node, Track

    from dataclass.spotify_track import SpotifyTrack


LOGGER = create_logger('jockey_helpers', debug=DEBUG_ENABLED)
T = TypeVar('T')


def check_similarity_weighted(actual: str, candidate: str, candidate_rank: int) -> int:
    """
    Checks the similarity between two strings using a weighted average
    of a given similarity score and the results of multiple fuzzy string
    matching algorithms. Meant for refining search results that are
    already ranked.

    :param actual: The actual string.
    :param candidate: The candidate string, i.e. from a search result.
    :param candidate_rank: The rank of the candidate, from 0 to 100.
    :return: An integer from 0 to 100, where 100 is the closest match.
    """
    naive = check_similarity(actual, candidate) * 100
    tsr = fuzz.token_set_ratio(actual, candidate)
    tsor = fuzz.token_sort_ratio(actual, candidate)
    ptsr = fuzz.partial_token_sort_ratio(actual, candidate)

    return int(
        (naive * 0.7) +
        (tsr * 0.12) +
        (candidate_rank * 0.08) +
        (tsor * 0.06) +
        (ptsr * 0.04)
    )


def rank_results(
    query: str,
    results: List[T],
    result_type: SearchType
) -> List[Tuple[T, int]]:
    """
    Ranks search results based on similarity to a fuzzy query.

    :param query: The query to check against.
    :param results: The results to rank. Can be mafic.Track, dataclass.SpotifyTrack,
        or any object with a title and author string attribute.
    :param result_type: The type of result. See ResultType.
    :return: A list of tuples containing the result and its similarity to the query.
    """
    # Rank results
    similarities = [
        check_similarity_weighted(
            query,
            f'{result.title} {result.author}',  # type: ignore
            100 - round(i * (100 / len(results)))
        )
        for i, result in enumerate(results)
    ]
    ranked = sorted(zip(results, similarities), key=lambda x: x[1], reverse=True)

    # Print confidences for debugging
    type_name = 'YouTube'
    if result_type == SearchType.SPOTIFY_SEARCH:
        type_name = 'Spotify'
    elif result_type == SearchType.DEEZER_SEARCH:
        type_name = 'Deezer'
    LOGGER.debug('%s results and confidences for "%s":', type_name, query)
    for result, confidence in ranked:
        LOGGER.debug(
            '  %3d  %-20s\t%-25s',
            confidence,
            result.author[:20], # type: ignore
            result.title[:25]   # type: ignore
        )

    return ranked


async def find_lavalink_track(
    node: 'Node',
    item: QueueItem,
    deezer_enabled: bool = False
) -> 'Track':
    """
    Finds a matching playable Lavalink track for a QueueItem.
    """
    results = []

    # Use ISRC if present
    if item.isrc is not None:
        # Try to match ISRC on Deezer if enabled
        if deezer_enabled:
            try:
                result = await get_deezer_track(node, item.isrc)
            except LavalinkSearchError:
                LOGGER.warning(
                    'No Deezer match for ISRC %s `%s\'',
                    item.isrc,
                    item.title
                )
            else:
                results.append(result)
                LOGGER.debug(
                    'Matched ISRC %s `%s\' on Deezer',
                    item.isrc,
                    item.title
                )

        # Try to match ISRC on YouTube
        if len(results) == 0:
            try:
                results = await get_youtube_matches(
                    node,
                    f'"{item.isrc}"',
                    desired_duration_ms=item.duration
                )
            except LavalinkSearchError:
                LOGGER.warning(
                    'No YouTube match for ISRC %s `%s\'',
                    item.isrc,
                    item.title
                )
            else:
                LOGGER.debug(
                    'Matched ISRC %s `%s\' on YouTube',
                    item.isrc,
                    item.title
                )

    # Fallback to metadata search
    query = f'{item.title} {item.artist}'
    if len(results) == 0:
        LOGGER.error(
            'No ISRC match for `%s\'. Falling back to metadata search.',
            item.title
        )
        item.is_imperfect = True

        # Try to match on Deezer if enabled
        if deezer_enabled:
            try:
                dz_results = await get_deezer_matches(
                    node,
                    query,
                    desired_duration_ms=item.duration
                )
            except LavalinkSearchError:
                LOGGER.warning(
                    'No Deezer results for `%s\'',
                    item.title
                )
            else:
                # Use top result if it's good enough
                ranked = rank_results(
                    query,
                    dz_results,
                    SearchType.DEEZER_SEARCH
                )
                if ranked[0][1] >= CONFIDENCE_THRESHOLD:
                    LOGGER.warning(
                        'Using Deezer result `%s\' (%s) for `%s\'',
                        ranked[0][0].title,
                        ranked[0][0].lavalink_track.identifier,
                        item.title
                    )
                    results.append(ranked[0][0])
                else:
                    LOGGER.warning(
                        'No similar Deezer results for `%s\'',
                        item.title
                    )

        if len(results) == 0:
            try:
                yt_results = await get_youtube_matches(
                    node,
                    query,
                    desired_duration_ms=item.duration
                )
            except LavalinkSearchError as err:
                LOGGER.error(err.message)
                raise

            # Use top result
            ranked = rank_results(
                query,
                yt_results,
                SearchType.YOUTUBE
            )
            LOGGER.warning(
                'Using YouTube result `%s\' (%s) for `%s\'',
                ranked[0][0].title,
                ranked[0][0].lavalink_track.identifier,
                item.title
            )
            results.append(ranked[0][0])

    # Save Lavalink result
    return results[0].lavalink_track


async def parse_query(
    node: 'Node',
    spotify: Spotify,
    query: str,
    requester: int
) -> List[QueueItem]:
    """
    Parse a query and return a list of QueueItems.

    :param node: The Lavalink node to use for searching. Must be an instance of mafic.Node.
    :param spotify: The Spotify client to use for searching. See utils/spotify_client.py.
    :param query: The query to parse. Can be plain language or a URL.
    :param requester: The ID of the user who requested the track.
    """
    query_is_url = check_url(query)
    if query_is_url:
        if check_spotify_url(query):
            # Query is a Spotify URL.
            return await parse_spotify_query(spotify, query, requester)
        if check_youtube_url(query) or check_ytmusic_url(query):
            # Query is a YouTube URL.
            return await parse_youtube_query(node, query, requester)
        if check_youtube_playlist_url(query) or check_ytmusic_playlist_url(query):
            # Query is a YouTube playlist URL.
            return await parse_youtube_playlist(node, query, requester)
        if check_sc_url(query):
            # Query is a SoundCloud URL.
            return await parse_sc_query(node, query, requester)

        # Direct URL playback is deprecated
        raise JockeyException('Direct playback from unsupported URLs is deprecated')

    # Attempt to look for a matching track on Spotify
    try:
        results = spotify.search(query, limit=10)
    except SpotifyNoResultsError:
        pass
    else:
        # Return top result if it's good enough
        ranked = rank_results(query, results, SearchType.SPOTIFY_SEARCH)
        if ranked[0][1] >= CONFIDENCE_THRESHOLD:
            track = ranked[0][0]
            return [QueueItem(
                requester=requester,
                title=track.title,
                artist=track.artist,
                spotify_id=track.spotify_id,
                duration=track.duration_ms,
                artwork=track.artwork,
                isrc=track.isrc
            )]

    # Get matching tracks from YouTube
    results = await get_youtube_matches(node, query, auto_filter=False)

    # Return top result
    ranked = rank_results(query, results, SearchType.YOUTUBE)
    result = ranked[0][0]
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
    """
    Parse a SoundCloud query and return a list of QueueItems.
    See parse_query() for more information.
    """
    try:
        # Get results with Lavalink
        tracks = await get_soundcloud_matches(node, query)
    except Exception as exc:
        raise LavalinkInvalidIdentifierError(
            f'Entity {query} is private, nonexistent, or has no stream URL'
        ) from exc

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
    """
    Parse a Spotify query and return a list of QueueItems.
    See parse_query() for more information.
    """
    # Get artwork for Spotify album/playlist
    sp_type, sp_id = get_spinfo_from_url(query)

    new_tracks = []
    track_queue: List['SpotifyTrack']
    try:
        if sp_type == 'track':
            # Get track details from Spotify
            track_queue = [spotify.get_track(sp_id)]
        else:
            # Get playlist or album tracks from Spotify
            track_queue = spotify.get_tracks(sp_type, sp_id)[2]
    except SpotifyException as exc:
        if exc.http_status == 404:
            # No tracks.
            raise SpotifyNoResultsError(
                f'The {sp_type} does not exist or is private.'
            ) from exc

        raise SpotifyNoResultsError(
            f'An error occurred while fetching the playlist: {exc.msg}'
        ) from exc

    if len(track_queue) < 1:
        if sp_type == 'track':
            # No tracks.
            raise SpotifyNoResultsError('Track does not exist or is private.')
        raise SpotifyNoResultsError('Playlist is empty.')

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
    """
    Parse a YouTube playlist query and return a list of QueueItems.
    See parse_query() for more information.
    """
    try:
        # Get playlist tracks from YouTube
        playlist_id = get_ytlistid_from_url(query)
        tracks = await get_youtube_matches(
            node,
            f'https://youtube.com/playlist?list={playlist_id}'
        )
    except Exception as exc:
        # No tracks.
        raise LavalinkInvalidIdentifierError(
            query,
            'Playlist is empty, private, or nonexistent'
        ) from exc

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
    """
    Parse a non-playlist YouTube query and return a list of QueueItems.
    See parse_query() for more information.
    """
    # Is it a video?
    try:
        video_id = get_ytid_from_url(query)

        # Get the video's details
        video = await get_youtube_matches(node, video_id)
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
    except Exception as exc:
        raise LavalinkInvalidIdentifierError(
            query,
            'Only YouTube video and playlist URLs are supported.'
        ) from exc
