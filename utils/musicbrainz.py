"""
Utility functions for interfacing with the MusicBrainz API.
"""

from typing import TYPE_CHECKING, Optional, Tuple

from requests import HTTPError, Timeout, get

from .constants import DURATION_THRESHOLD, MUSICBRAINZ_API_BASE_URL, USER_AGENT
from .fuzzy import check_similarity_weighted

if TYPE_CHECKING:
    from logging import Logger

    from dataclass.queue_item import QueueItem


def mb_lookup(logger: 'Logger', track: 'QueueItem') -> Tuple[str | None, str | None]:
    """
    Looks up a track on MusicBrainz and returns a tuple containing
    a matching MusicBrainz ID and ISRC, if available.
    """
    # Build MusicBrainz query
    assert track.title is not None and track.artist is not None
    query = f'recording:{track.title} && artist:{track.artist}'
    if track.album is not None:
        query += f' && release:{track.album}'

    # Perform search
    response = get(
        str(MUSICBRAINZ_API_BASE_URL / 'recording'),
        headers={
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        },
        params={
            'query': query,
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

    # Parse response
    parsed = response.json()
    if len(parsed['recordings']) == 0:
        logger.error(
            'No results found for track `%s\' on MusicBrainz',
            track.title
        )
        return None, None

    # Filter by duration difference
    results = [
        result
        for result in parsed['recordings']
        if 'length' in result and abs(track.duration - result['length']) < DURATION_THRESHOLD
    ]
    if len(results) == 0:
        logger.error(
            'No results found for track `%s\' on MusicBrainz',
            track.title
        )
        return None, None

    # Sort remaining results by similarity and ISRC presence
    query = f'{track.title} {track.artist}'
    best_match = results[0]
    if len(results) > 1:
        similarities = [
            check_similarity_weighted(
                query,
                f'{result["title"]} {result["artist-credit"][0]["name"]}',
                result['score']
            ) for result in results
        ]
        isrc_presence = [
            'isrcs' in result and len(result['isrcs']) > 0
            for result in results
        ]
        ranked = sorted(
            zip(results, similarities, isrc_presence),
            key=lambda x: (x[1], x[2]),
            reverse=True
        )
        best_match = ranked[0][0]

        # Print confidences for debugging
        logger.debug('MusicBrainz results and confidences for "%s":', query)
        for result, confidence, has_isrc in ranked:
            logger.debug(
                '  %3d  %-20s  %-20s  isrc=%s',
                confidence,
                result['artist-credit'][0]['name'][:20],
                result['title'][:20],
                has_isrc
            )

    # Extract ID and ISRC
    mbid = best_match['id']
    isrc = None
    if 'isrcs' in best_match and len(best_match['isrcs']) > 0:
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
