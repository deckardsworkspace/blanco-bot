"""
Utility functions for interfacing with the MusicBrainz API.
"""

from typing import TYPE_CHECKING, Optional, Tuple

from requests import HTTPError, Timeout, get

from .constants import MUSICBRAINZ_API_BASE_URL, USER_AGENT
from .fuzzy import check_similarity

if TYPE_CHECKING:
    from logging import Logger

    from dataclass.queue_item import QueueItem


def mb_lookup(logger: 'Logger', track: 'QueueItem') -> Tuple[str | None, str | None]:
    """
    Looks up a track on MusicBrainz and returns a tuple containing
    a matching MusicBrainz ID and ISRC, if available.
    """
    response = get(
        str(MUSICBRAINZ_API_BASE_URL / 'recording'),
        headers={
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        },
        params={
            'query': f'recording:{track.title} && artist:{track.artist}',
            'limit': 10,
            'inc': 'isrcs',
            'fmt': 'json'
        },
        timeout=5.0
    )

    try:
        response.raise_for_status()
    except HTTPError as err:
        logger.error(
            'Error %d looking up track `%s\' on MusicBrainz.\n%s',
            err.response.status_code,
            track.title,
            err
        )
        raise
    except Timeout:
        logger.warning(
            'Timed out while looking up track `%s\' on MusicBrainz',
            track.title
        )
        return None, None

    parsed = response.json()
    if len(parsed['recordings']) == 0:
        logger.error(
            'No results found for track `%s\' on MusicBrainz',
            track.title
        )
        return None, None

    # Find best match
    best_match_avg = 0.0
    best_match = None
    for match in parsed['recordings']:
        title_score, artist_score = 0.0, 0.0

        if track.title is not None:
            title_score = check_similarity(track.title, match['title'])
        if track.artist is not None:
            artist_score = check_similarity(track.artist, match['artist-credit'][0]['name'])
        if track.duration is not None and 'length' in match:
            mb_diff = track.duration - match['length']
            duration_score = abs(mb_diff) / track.duration
            if duration_score > 0.1:
                logger.debug(
                    'Skipping MusicBrainz result `%s\' '
                    'for `%s\': duration mismatch (%.2f s)',
                    match['title'],
                    track.title,
                    mb_diff / 1000
                )
                continue

        avg = (title_score + artist_score) / 2
        if avg > 0.8 and avg > best_match_avg:
            best_match_avg = avg
            best_match = match

    if best_match is None:
        logger.error(
            'No results found for track `%s\' on MusicBrainz',
            track.title
        )
        return None, None

    # Extract ID and ISRC
    mbid = best_match['id']
    isrc = None
    if 'isrcs' in best_match:
        isrc = best_match['isrcs'][0]

    return mbid, isrc


def mb_lookup_isrc(logger: 'Logger', track: 'QueueItem') -> Optional[str]:
    """
    Looks up a track by its ISRC on MusicBrainz and returns a MusicBrainz ID.
    """
    assert track.isrc is not None
    response = get(
        str(MUSICBRAINZ_API_BASE_URL / 'isrc' / track.isrc.upper()),
        headers={
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        },
        params={'fmt': 'json'},
        timeout=5.0
    )

    try:
        response.raise_for_status()
    except HTTPError:
        logger.error(
            'ISRC %s (`%s\') is not on MusicBrainz',
            track.isrc,
            track.title
        )
        raise
    except Timeout:
        logger.warning(
            'Timed out while looking up track `%s\' (%s) on MusicBrainz',
            track.title,
            track.isrc
        )
        return None

    parsed = response.json()
    if len(parsed['recordings']) == 0:
        logger.error(
            'No results found for track `%s\' (%s) on MusicBrainz',
            track.title,
            track.isrc
        )
        return None

    return parsed['recordings'][0]['id']
