from dataclass.lavalink_result import LavalinkResult
from typing import List, Optional, Tuple, TYPE_CHECKING
from .exceptions import LavalinkInvalidIdentifierError, LavalinkInvalidIdentifierError, LavalinkSearchError
import difflib
if TYPE_CHECKING:
    from lavalink.models import AudioTrack, DefaultPlayer


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


def parse_result(result: 'AudioTrack') -> LavalinkResult:
    return LavalinkResult(
        title=result.title,
        author=result.author,
        duration_ms=result.duration,
        url=result.uri,
        lavalink_track=result
    )


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


async def get_tracks(player: 'DefaultPlayer', id_or_url: str) -> Tuple[Optional[str], List[LavalinkResult]]:
    try:
        result = await player.node.get_tracks(id_or_url)
        if result['loadType'] == 'LOAD_FAILED':
            reason = result['exception']['message']
            raise LavalinkInvalidIdentifierError(id_or_url, reason=reason)
        elif result['loadType'] == 'NO_MATCHES':
            raise LavalinkSearchError(id_or_url, reason=f'No matches found for "{id_or_url}"')
    except Exception as e:
        raise LavalinkSearchError(id_or_url, reason=f'Could not get tracks for "{id_or_url}" ({e})')
    else:
        tracks = result['tracks']
        if isinstance(result['playlistInfo'], dict) and 'name' in result['playlistInfo']:
            return result['playlistInfo']['name'], [parse_result(track) for track in tracks]
        else:
            return None, [parse_result(track) for track in tracks]


async def get_youtube_matches(player: 'DefaultPlayer', query: str, desired_duration_ms: int = 0, automatic: bool = True) -> List[LavalinkResult]:
    results: List[LavalinkResult] = []

    search = await player.node.get_tracks(f'ytsearch:{query}')
    if len(search['tracks']) == 0 or search['loadType'] == 'NO_MATCHES':
        raise LavalinkSearchError(query, reason='No results found')
    elif search['loadType'] != 'SEARCH_RESULT':
        raise LavalinkSearchError(query, reason='Invalid search result')

    search_results = search['tracks']
    for result in search_results:
        if not result.duration:
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
    if desired_duration_ms > 0:
        results.sort(key=lambda x: (1 - check_similarity(query, x.title), abs(x.duration_ms - desired_duration_ms)))
    else:
        results.sort(key=lambda x: 1 - check_similarity(query, x.title))

    return results
