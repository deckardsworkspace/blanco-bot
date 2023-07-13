from dataclass.lavalink_result import LavalinkResult
from mafic import Playlist, SearchType
from typing import List, Optional, Tuple, TYPE_CHECKING
from .exceptions import LavalinkSearchError
import difflib
if TYPE_CHECKING:
    from mafic import Node, Track


blacklist = (
    '3d'
    '8d',
    'cover',
    'instrumental',
    'karaoke',
    'live',
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


async def get_tracks(node: 'Node', query: str, search_type: str = 'EMPTY') -> Tuple[Optional[str], List[LavalinkResult]]:
    # Check if search type is valid
    try:
        _ = SearchType(search_type)
    except ValueError:
        raise ValueError(f'Invalid search type "{search_type}"')
    
    try:
        result = await node.fetch_tracks(query, search_type=search_type)
        if result is None:
            raise LavalinkSearchError(query, reason=f'No matches found for "{query}"')
    except Exception as e:
        raise LavalinkSearchError(query, reason=f'Could not get tracks for "{query}" ({e})')
    else:
        if isinstance(result, Playlist):
            return result.name, [parse_result(track) for track in result.tracks]
        else:
            return None, [parse_result(track) for track in result]


async def get_youtube_matches(node: 'Node', query: str, desired_duration_ms: Optional[int] = 0, automatic: bool = True) -> List[LavalinkResult]:
    results: List[LavalinkResult] = []

    search = await node.fetch_tracks(query, search_type=SearchType.YOUTUBE.value)
    if isinstance(search, Playlist) and len(search.tracks) == 0:
        raise LavalinkSearchError(query, reason='Playlist is empty')
    elif (isinstance(search, list) and len(search) == 0) or search is None:
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
            for word in blacklist:
                if word in result.title.lower() and not word in query.lower():
                    valid = False
                    break

        if valid:
            results.append(parse_result(result))

    # Sort by descending similarity
    if desired_duration_ms is not None:
        results.sort(key=lambda x: (1 - check_similarity(query, x.title), abs(x.duration_ms - desired_duration_ms)))
    else:
        results.sort(key=lambda x: 1 - check_similarity(query, x.title))

    return results
