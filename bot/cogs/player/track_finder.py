from typing import TYPE_CHECKING, List, Optional, Tuple

from mafic import SearchType

from bot.database.redis import REDIS
from bot.utils.constants import CONFIDENCE_THRESHOLD
from bot.utils.exceptions import LavalinkSearchError
from bot.utils.logger import create_logger
from bot.utils.musicbrainz import annotate_track

from .jockey_helpers import rank_results
from .lavalink_client import get_deezer_matches, get_deezer_track, get_youtube_matches

if TYPE_CHECKING:
  from mafic import Node, Track

  from bot.dataclass.lavalink_result import LavalinkResult
  from bot.dataclass.queue_item import QueueItem

  from .lavalink_client import LavalinkSearchError

LOGGER = create_logger('track_finder')


async def find_lavalink_track(
  node: 'Node',
  item: QueueItem,
  /,
  deezer_enabled: bool = False,
  in_place: bool = False,
  lookup_mbid: bool = False,
) -> 'Track':
  """
  Finds a matching playable Lavalink track for a QueueItem.

  :param node: The Lavalink node to use for searching. Must be an instance of mafic.Node.
  :param item: The QueueItem to find a track for.
  :param deezer_enabled: Whether to use Deezer for searching.
  :param in_place: Whether to modify the QueueItem in place.
  :param lookup_mbid: Whether to look up the MBID for the track.
  """
  results = []

  cached, redis_key, redis_key_type = _get_cached_track(item)
  if cached is not None:
    LOGGER.info('Found cached Lavalink track for Spotify ID %s', item.spotify_id)
    track = await node.decode_track(cached)
    if in_place:
      item.lavalink_track = track

    return track

  if item.isrc is None or lookup_mbid:
    annotate_track(item)

  if item.isrc is not None:
    if deezer_enabled:
      await _append_deezer_results_for_isrc(
        results=results,
        node=node,
        isrc=item.isrc,
        title=item.title,
      )

    await _append_youtube_results_for_isrc(
      results=results,
      node=node,
      isrc=item.isrc,
      title=item.title,
      duration_ms=item.duration,
    )
  else:
    LOGGER.warning(
      "`%s' has no ISRC. Scrobbling might fail for this track.", item.title
    )
    item.is_imperfect = True

  # Fallback to metadata search
  if len(results) == 0:
    query = f'{item.title} {item.artist}'
    LOGGER.warning(
      "No matches for ISRC %s `%s'. Falling back to metadata search.",
      item.isrc,
      item.title,
    )

    if deezer_enabled:
      await _append_deezer_results_for_metadata(
        results=results,
        node=node,
        query=query,
        title=item.title,
        duration_ms=item.duration,
      )

    await _append_youtube_results_for_metadata(
      results=results,
      node=node,
      query=query,
      title=item.title,
      duration_ms=item.duration,
    )

  if len(results) == 0:
    raise LavalinkSearchError('No results found')

  lavalink_track = results[0].lavalink_track
  if in_place:
    item.lavalink_track = lavalink_track
  _set_cached_track(lavalink_track.id, key=redis_key, key_type=redis_key_type)

  return lavalink_track


def _get_cached_track(
  item: QueueItem,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
  redis_key = None
  redis_key_type = None
  if item.spotify_id is not None:
    redis_key = item.spotify_id
    redis_key_type = 'spotify_id'
  elif item.isrc is not None:
    redis_key = item.isrc
    redis_key_type = 'isrc'

  cached = None
  if REDIS is not None and redis_key is not None and redis_key_type is not None:
    cached = REDIS.get_lavalink_track(redis_key, key_type=redis_key_type)

  return cached, redis_key, redis_key_type


def _set_cached_track(
  lavalink_track: str,
  key: Optional[str] = None,
  key_type: Optional[str] = None,
):
  if REDIS is not None and key_type is not None and key is not None:
    REDIS.set_lavalink_track(key, lavalink_track, key_type=key_type)


async def _append_deezer_results_for_isrc(
  results: List['LavalinkResult'],
  node: 'Node',
  isrc: str,
  title: Optional[str] = None,
) -> List['LavalinkResult']:
  try:
    result = await get_deezer_track(node, isrc)
  except LavalinkSearchError:
    LOGGER.warning("No Deezer match for ISRC %s `%s'", isrc, title)
  else:
    results.append(result)
    LOGGER.debug("Matched ISRC %s `%s' on Deezer", isrc, title)

  return results


async def _append_deezer_results_for_metadata(
  results: List['LavalinkResult'],
  node: 'Node',
  query: str,
  title: Optional[str] = None,
  duration_ms: Optional[int] = None,
):
  try:
    dz_results = await get_deezer_matches(
      node, query, desired_duration_ms=duration_ms, auto_filter=True
    )
  except LavalinkSearchError:
    LOGGER.warning("No Deezer results for `%s'", title)
  else:
    ranked = rank_results(query, dz_results, SearchType.DEEZER_SEARCH)
    if ranked[0][1] >= CONFIDENCE_THRESHOLD:
      LOGGER.warning(
        "Using Deezer result `%s' (%s) for `%s'",
        ranked[0][0].title,
        ranked[0][0].lavalink_track.identifier,
        title,
      )
      results.append(ranked[0][0])
    else:
      LOGGER.warning("No similar Deezer results for `%s'", title)


async def _append_youtube_results_for_isrc(
  results: List['LavalinkResult'],
  node: 'Node',
  isrc: str,
  title: Optional[str] = None,
  duration_ms: Optional[int] = None,
):
  if len(results) > 0:
    return

  try:
    results.extend(
      await get_youtube_matches(node, f'"{isrc}"', desired_duration_ms=duration_ms)
    )
  except LavalinkSearchError:
    LOGGER.warning("No YouTube match for ISRC %s `%s'", isrc, title)
  else:
    LOGGER.debug("Matched ISRC %s `%s' on YouTube", isrc, title)


async def _append_youtube_results_for_metadata(
  results: List['LavalinkResult'],
  node: 'Node',
  query: str,
  title: Optional[str] = None,
  duration_ms: Optional[int] = None,
):
  try:
    yt_results = await get_youtube_matches(node, query, desired_duration_ms=duration_ms)
  except LavalinkSearchError:
    LOGGER.warning("No YouTube results for `%s'", title)
  else:
    ranked = rank_results(query, yt_results, SearchType.YOUTUBE)
    LOGGER.warning(
      "Using YouTube result `%s' (%s) for `%s'",
      ranked[0][0].title,
      ranked[0][0].lavalink_track.identifier,
      title,
    )
    results.append(ranked[0][0])
