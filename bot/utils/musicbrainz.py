"""
Utility functions for interfacing with the MusicBrainz API.
"""

from typing import TYPE_CHECKING, Optional, Tuple

from ratelimit import limits, sleep_and_retry
from requests import HTTPError, Timeout, get
from requests.status_codes import codes

from bot.database.redis import REDIS

from .constants import DURATION_THRESHOLD, MUSICBRAINZ_API_BASE_URL, USER_AGENT
from .fuzzy import check_similarity_weighted
from .logger import create_logger

if TYPE_CHECKING:
  from bot.models.queue_item import QueueItem


LOGGER = create_logger('musicbrainz')


@limits(calls=25, period=1)
@sleep_and_retry
def annotate_track(  # noqa: PLR0912
  track: 'QueueItem', *, in_place: bool = True
) -> Optional[Tuple[str | None, str | None]]:
  """
  Annotates a track with MusicBrainz ID and ISRC if they are not already present.

  Can be called up to 25 times per second, and will sleep and retry if this limit
  is exceeded. This is because MusicBrainz has a rate limit of 50 requests per second,
  but we need to make at most two requests per track (one to search for the track by ISRC,
  and one to search for it by title and artist if the ISRC search fails).

  TODO: Refactor to have fewer branches.

  :param track: The track to annotate. Must be an instance of
      dataclass.queue_item.QueueItem.
  :param in_place: Whether to modify the track in place. If False, a tuple containing
      the MusicBrainz ID and ISRC will be returned instead.
  """
  # Check if track has already been annotated
  if track.is_annotated:
    return track.mbid, track.isrc

  # Check if information is already cached
  mbid = track.mbid
  isrc = track.isrc
  mbid_cached = False
  isrc_cached = False
  if REDIS is not None:
    # Check for cached MusicBrainz ID
    if mbid is None and track.spotify_id is not None:
      mbid = REDIS.get_mbid(track.spotify_id)
      if mbid is not None:
        mbid_cached = True

    # Check for cached ISRC
    if isrc is None and track.spotify_id is not None:
      isrc = REDIS.get_isrc(track.spotify_id)
      if isrc is not None:
        isrc_cached = True

  # Lookup MusicBrainz ID and ISRC if not cached
  if mbid is None:
    if isrc is not None:
      LOGGER.info("Looking up MusicBrainz ID for `%s'", track.title)
      try:
        mbid = mb_lookup_isrc(track)
      except HTTPError as err:
        if err.response is not None and err.response.status_code == codes.not_found:
          mbid, isrc = mb_lookup(track)
        else:
          raise
    else:
      LOGGER.info("Looking up MusicBrainz ID and ISRC for `%s'", track.title)
      mbid, isrc = mb_lookup(track)

  # Log MusicBrainz ID if found
  if track.mbid is None and mbid is not None:
    if in_place:
      track.mbid = mbid
    if REDIS is not None and track.spotify_id is not None:
      REDIS.set_mbid(track.spotify_id, mbid)

    LOGGER.info(
      "Found %sMusicBrainz ID `%s' for `%s'",
      'cached ' if mbid_cached else '',
      track.mbid,
      track.title,
    )

  # Log ISRC if found
  if track.isrc is None and isrc is not None:
    if in_place:
      track.isrc = isrc
    if REDIS is not None and track.spotify_id is not None:
      REDIS.set_isrc(track.spotify_id, isrc)

    LOGGER.info(
      "Found %sISRC `%s' for `%s'",
      'cached ' if isrc_cached else '',
      isrc,
      track.title,
    )

  if in_place:
    # Signal that the track has been annotated
    track.is_annotated = True

  return mbid, isrc


def mb_lookup(track: 'QueueItem') -> Tuple[str | None, str | None]:
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
    headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'},
    params={'query': query, 'limit': '10', 'inc': 'isrcs', 'fmt': 'json'},
    timeout=5.0,
  )
  try:
    response.raise_for_status()
  except HTTPError as err:
    LOGGER.error(
      "Error %d looking up track `%s' on MusicBrainz.\n%s",
      err.response.status_code if err.response is not None else -1,
      track.title,
      err,
    )
    raise
  except Timeout:
    LOGGER.warning("Timed out while looking up track `%s' on MusicBrainz", track.title)
    return None, None

  # Parse response
  parsed = response.json()
  if len(parsed['recordings']) == 0:
    LOGGER.error("No results found for track `%s' on MusicBrainz", track.title)
    return None, None

  # Filter by duration difference
  results = [
    result
    for result in parsed['recordings']
    if 'length' in result
    and abs(track.duration - result['length']) < DURATION_THRESHOLD
  ]
  if len(results) == 0:
    LOGGER.error("No results found for track `%s' on MusicBrainz", track.title)
    return None, None

  # Sort remaining results by similarity and ISRC presence
  query = f'{track.title} {track.artist}'
  best_match = results[0]
  if len(results) > 1:
    similarities = [
      check_similarity_weighted(
        query,
        f"{result['title']} {result['artist-credit'][0]['name']}",
        result['score'],
      )
      for result in results
    ]
    isrc_presence = [
      'isrcs' in result and len(result['isrcs']) > 0 for result in results
    ]
    ranked = sorted(
      zip(results, similarities, isrc_presence),
      key=lambda x: (x[1], x[2]),
      reverse=True,
    )
    best_match = ranked[0][0]

    # Print confidences for debugging
    LOGGER.debug('MusicBrainz results and confidences for "%s":', query)
    for result, confidence, has_isrc in ranked:
      LOGGER.debug(
        '  %3d  %-20s  %-20s  isrc=%s',
        confidence,
        result['artist-credit'][0]['name'][:20],
        result['title'][:20],
        has_isrc,
      )

  # Extract ID and ISRC
  mbid = best_match['id']
  isrc = None
  if 'isrcs' in best_match and len(best_match['isrcs']) > 0:
    isrc = best_match['isrcs'][0]

  return mbid, isrc


def mb_lookup_isrc(track: 'QueueItem') -> Optional[str]:
  """
  Looks up a track by its ISRC on MusicBrainz and returns a MusicBrainz ID.
  """
  assert track.isrc is not None
  response = get(
    str(MUSICBRAINZ_API_BASE_URL / 'isrc' / track.isrc.upper()),
    headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'},
    params={'fmt': 'json'},
    timeout=5.0,
  )

  try:
    response.raise_for_status()
  except HTTPError:
    LOGGER.error("ISRC %s (`%s') is not on MusicBrainz", track.isrc, track.title)
    raise
  except Timeout:
    LOGGER.warning(
      "Timed out while looking up track `%s' (%s) on MusicBrainz",
      track.title,
      track.isrc,
    )
    return None

  parsed = response.json()
  if len(parsed['recordings']) == 0:
    LOGGER.error(
      "No results found for track `%s' (%s) on MusicBrainz",
      track.title,
      track.isrc,
    )
    return None

  return parsed['recordings'][0]['id']
