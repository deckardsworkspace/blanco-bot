from dataclass.lavalink_result import LavalinkResult
from lavalink.models import DefaultPlayer
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from .exceptions import LavalinkInvalidIdentifierError, LavalinkInvalidIdentifierError, LavalinkSearchError
from .url_check import check_youtube_url
import re


blacklist = ('karaoke', 'live', 'instrumental', 'piano', 'cover', 'minus one', 'reverb', 'slowed', 'remix', 'mashup')


def parse_result(result: Dict[str, str]) -> LavalinkResult:
    return LavalinkResult(
        title=result['info']['title'],
        author=result['info']['author'],
        duration_ms=result['info']['length'],
        url=result['info']['uri'],
        lavalink_track=result
    )


async def get_tracks(player: DefaultPlayer, id_or_url: str) -> Tuple[Optional[str], List[LavalinkResult]]:
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
        if len(result['playlistInfo'].keys()) > 0:
            return result['playlistInfo']['name'], [parse_result(track) for track in tracks]
        else:
            return None, [parse_result(track) for track in tracks]


async def get_youtube_matches(player: DefaultPlayer, query: str, desired_duration_ms: int = 0, automatic: bool = True) -> List[LavalinkResult]:
    results: List[LavalinkResult] = []

    try:
        search = await player.node.get_tracks(f'ytsearch:{query}')
        if search['loadType'] != 'SEARCH_RESULT':
            raise LavalinkSearchError(query, reason='Invalid search result')
        elif len(search['tracks']) == 0:
            raise LavalinkSearchError(query, reason='No results found')
    except:
        raise LavalinkSearchError(query)
    else:
        search_results = search['tracks']
        for result in search_results:
            if 'length' not in result['info'].keys() or result['info']['length'] is None:
                # Can't play a track with no duration
                continue

            # Skip karaoke, live, instrumental etc versions
            # if the original query did not ask for it
            valid = True
            if automatic:
                for word in blacklist:
                    if word in result['info']['title'].lower() and not word in query.lower():
                        valid = False
                        break

            if valid:
                results.append(parse_result(result))

    if desired_duration_ms > 0:
        if abs(results[0].duration_ms - desired_duration_ms) < 3500:
            # First result is within acceptable range of desired duration,
            # so we just need to sort the elements after the first one.
            saved_result = results[0]
            results = sorted(results[1:], key=lambda x: abs(x.duration_ms - desired_duration_ms))
            results.insert(0, saved_result)
        else:
            # First result is outside acceptable range, so we sort everything
            # results by distance to desired duration.
            results.sort(key=lambda x: abs(x.duration_ms - desired_duration_ms))
    return results


def get_sctype_from_url(url: str) -> bool:
    """
    Determine SoundCloud entity type from URL.

    Returns
    -------
    True if URL is a SoundCloud track, False if URL is a SoundCloud playlist.
    """
    if url.startswith(('soundcloud', 'www')):
        url = 'http://' + url

    query = urlparse(url)
    path = [x for x in query.path.split('/') if x]
    if len(path) == 1:
        raise LavalinkInvalidIdentifierError(url, reason='SoundCloud URL does not point to a track or set.')
    elif len(path) == 2 and path[1] != 'sets':
        return True
    elif path[1] == 'sets':
        return False
    else:
        raise LavalinkInvalidIdentifierError(url, reason='Unrecognized SoundCloud URL.')


def get_ytid_from_url(url: str, id_type: str = 'v') -> str:
    # https://gist.github.com/kmonsoor/2a1afba4ee127cce50a0
    if url.startswith(('youtu', 'www')):
        url = 'http://' + url

    query = urlparse(url)
    if 'youtube' in query.hostname:
        if re.match(r"^/watch", query.path):
            if len(query.query):
                return parse_qs(query.query)[id_type][0]
            return query.path.split("/")[2]
        elif query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    elif 'youtu.be' in query.hostname:
        return query.path[1:]
    
    raise LavalinkInvalidIdentifierError(url, reason='Could not get playlist ID from YouTube URL')


def get_ytlistid_from_url(url: str) -> str:
    if url.startswith(('youtu', 'www')):
        url = 'http://' + url

    query = urlparse(url)
    if 'youtube' in query.hostname and len(query.query):
        return parse_qs(query.query)['list'][0]
    
    raise LavalinkInvalidIdentifierError(url, reason='Not a valid YouTube URL')
