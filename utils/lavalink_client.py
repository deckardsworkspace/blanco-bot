"""
Lavalink search helpers, which augment the basic search endpoint
with fuzzy search and exclusion of non-official track versions
(remixes, etc.) that the user didn't specifically ask for.
"""

import difflib
from typing import TYPE_CHECKING, List, Optional, Tuple

from mafic import Playlist, SearchType, TrackLoadException

from dataclass.lavalink_result import LavalinkResult

from .exceptions import LavalinkSearchError

if TYPE_CHECKING:
    from mafic import Node, Track


BLACKLIST = (
    '3d'
    '8d',
    'cover',
    'instrumental',
    'karaoke',
    'live',
    'loop',
    'mashup',
    'minus one',
    'performance',
    'piano',
    'remix',
    'rendition',
    'reverb',
    'slowed'
)


def parse_result(result: 'Track') -> LavalinkResult:
    """
    Parses a Lavalink track result into a LavalinkResult object.
    """
    parsed = LavalinkResult(
        title=result.title,
        author=result.author,
        duration_ms=result.length,
        artwork_url=result.artwork_url,
        lavalink_track=result
    )
    if result.uri is not None:
        parsed.url = result.uri

    return parsed


def check_similarity(actual: str, candidate: str) -> float:
    """
    Checks the similarity between two strings. Meant for comparing
    song titles and artists with search results.

    :param actual: The actual string.
    :param candidate: The candidate string, i.e. from a search result.
    :return: A float between 0 and 1, where 1 is a perfect match.
    """
    actual_words = actual.lower().split(' ')
    candidate_words = candidate.lower().split(' ')
    intersection = set(actual_words).intersection(set(candidate_words))

    # Get words not in intersection
    unmatched_words = [word for word in actual_words if word not in intersection]
    for word in unmatched_words:
        # Look for close matches
        close_matches = difflib.get_close_matches(word, candidate_words, cutoff=0.8)
        if len(close_matches) > 0:
            intersection.add(close_matches[0])

    return len(intersection) / len(actual_words)


async def get_tracks(
    node: 'Node',
    query: str,
    search_type: str = 'EMPTY'
) -> Tuple[Optional[str], List[LavalinkResult]]:
    """
    Gets tracks from Lavalink, and returns a list of LavalinkResult objects.
    """
    # Check if search type is valid
    try:
        _ = SearchType(search_type)
    except ValueError as exc:
        raise ValueError(f'Invalid search type "{search_type}"') from exc

    try:
        result = await node.fetch_tracks(query, search_type=search_type)
    except TrackLoadException as exc:
        raise LavalinkSearchError(
            query,
            reason=f'Could not get tracks for "{query}" ({exc})'
        ) from exc

    if result is None:
        raise LavalinkSearchError(query, reason=f'No matches found for "{query}"')

    if isinstance(result, Playlist):
        return result.name, [parse_result(track) for track in result.tracks]
    return None, [parse_result(track) for track in result]


async def get_deezer_track(node: 'Node', isrc: str) -> LavalinkResult:
    """
    Gets a Deezer track from Lavalink, and returns a LavalinkResult object.
    """
    search = await node.fetch_tracks(isrc, search_type=SearchType.DEEZER_ISRC.value)

    if (isinstance(search, list) and len(search) == 0) or search is None:
        raise LavalinkSearchError(isrc, reason='No results found')

    search_result = search[0] if isinstance(search, list) else search.tracks[0]
    return parse_result(search_result)


async def get_youtube_matches(
    node: 'Node',
    query: str,
    desired_duration_ms: Optional[int] = 0,
    automatic: bool = True
) -> List[LavalinkResult]:
    """
    Gets YouTube tracks from Lavalink, and returns a list of LavalinkResult objects.
    """
    results: List[LavalinkResult] = []

    search = await node.fetch_tracks(query, search_type=SearchType.YOUTUBE.value)
    if isinstance(search, Playlist) and len(search.tracks) == 0:
        raise LavalinkSearchError(query, reason='Playlist is empty')
    if (isinstance(search, list) and len(search) == 0) or search is None:
        raise LavalinkSearchError(query, reason='No results found')

    search_results = search if isinstance(search, list) else search.tracks
    for result in search_results:
        if not result.length:
            # Can't play a track with no duration
            continue

        # Skip karaoke, live, instrumental etc versions
        # if the original query did not ask for it
        valid = True
        if automatic:
            for word in BLACKLIST:
                if word in result.title.lower() and not word in query.lower():
                    valid = False
                    break

        if valid:
            results.append(parse_result(result))

    # Sort by descending similarity
    if desired_duration_ms is not None:
        results.sort(
            key=lambda x: (1 - check_similarity(query, x.title),
                           abs(x.duration_ms - desired_duration_ms))
        )
    else:
        results.sort(key=lambda x: 1 - check_similarity(query, x.title))

    return results
