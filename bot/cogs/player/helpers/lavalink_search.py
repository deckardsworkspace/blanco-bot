"""
Lavalink search helpers, which augment the basic search endpoint
with fuzzy search and exclusion of non-official track versions
(remixes, etc.) that the user didn't specifically ask for.
"""

from typing import TYPE_CHECKING, List, Optional

from mafic import Playlist, SearchType, TrackLoadException

from bot.models.lavalink_result import LavalinkResult
from bot.utils.constants import BLACKLIST
from bot.utils.exceptions import LavalinkSearchError
from bot.utils.fuzzy import check_similarity

if TYPE_CHECKING:
  from mafic import Node, Track


def filter_results(query: str, search_results: List['Track']) -> List[LavalinkResult]:
  """
  Filters search results by removing karaoke, live, instrumental etc versions.
  """
  results = []

  for result in search_results:
    if not result.length:
      # Can't play a track with no duration
      continue

    # Skip karaoke, live, instrumental etc versions
    # if the original query did not ask for it
    valid = True
    for word in BLACKLIST:
      if word in result.title.lower() and word not in query.lower():
        valid = False
        break

    if valid:
      results.append(parse_result(result))

  return results


def parse_result(result: 'Track') -> LavalinkResult:
  """
  Parses a Lavalink track result into a LavalinkResult object.
  """
  parsed = LavalinkResult(
    title=result.title,
    author=result.author,
    duration_ms=result.length,
    artwork_url=result.artwork_url,
    lavalink_track=result,
  )
  if result.uri is not None:
    parsed.url = result.uri

  return parsed


async def get_deezer_matches(
  node: 'Node',
  query: str,
  desired_duration_ms: Optional[int] = None,
  auto_filter: bool = False,
) -> List[LavalinkResult]:
  """
  Gets Deezer tracks from Lavalink, and returns a list of LavalinkResult objects.

  :param node: The Lavalink node to use.
  :param query: The query to search for.
  :param desired_duration_ms: The desired duration of the track, in milliseconds.
  :param automatic: Whether to automatically filter results.
  """
  return await search_lavalink(
    node,
    query,
    search_type=SearchType.DEEZER_SEARCH.value,
    desired_duration_ms=desired_duration_ms,
    auto_filter=auto_filter,
  )


async def get_deezer_track(node: 'Node', isrc: str) -> LavalinkResult:
  """
  Gets a single Deezer track from Lavalink, and returns a LavalinkResult object.

  :param node: The Lavalink node to use.
  :param isrc: The ISRC to search for.
  """
  results = await search_lavalink(
    node, isrc, search_type=SearchType.DEEZER_ISRC.value, auto_filter=False
  )
  return results[0]


async def get_soundcloud_matches(
  node: 'Node',
  query: str,
  desired_duration_ms: Optional[int] = None,
  auto_filter: bool = False,
) -> List[LavalinkResult]:
  """
  Gets SoundCloud tracks from Lavalink, and returns a list of LavalinkResult objects.

  :param node: The Lavalink node to use.
  :param query: The query to search for.
  :param desired_duration_ms: The desired duration of the track, in milliseconds.
  :param automatic: Whether to automatically filter results.
  """
  return await search_lavalink(
    node,
    query,
    search_type=SearchType.SOUNDCLOUD.value,
    desired_duration_ms=desired_duration_ms,
    auto_filter=auto_filter,
  )


async def get_youtube_matches(
  node: 'Node',
  query: str,
  desired_duration_ms: Optional[int] = None,
  auto_filter: bool = False,
) -> List[LavalinkResult]:
  """
  Gets YouTube tracks from Lavalink, and returns a list of LavalinkResult objects.

  :param node: The Lavalink node to use.
  :param query: The query to search for.
  :param desired_duration_ms: The desired duration of the track, in milliseconds.
  :param automatic: Whether to automatically filter results.
  """
  return await search_lavalink(
    node,
    query,
    search_type=SearchType.YOUTUBE.value,
    desired_duration_ms=desired_duration_ms,
    auto_filter=auto_filter,
  )


async def search_lavalink(
  node: 'Node',
  query: str,
  search_type: str = SearchType.YOUTUBE.value,
  desired_duration_ms: Optional[int] = None,
  auto_filter: bool = False,
) -> List[LavalinkResult]:
  """
  Generic search function for Lavalink that returns a list of LavalinkResult objects.

  :param node: The Lavalink node to use.
  :param query: The query to search for.
  :param search_type: The search type to use. See mafic.SearchType.
  :param desired_duration_ms: The desired duration of the track, in milliseconds.
  :param automatic: Whether to automatically filter results.
  """
  try:
    search = await node.fetch_tracks(query, search_type=search_type)
  except TrackLoadException as exc:
    raise LavalinkSearchError(
      query, reason=f"Could not get tracks for `{query}': {exc.cause}"
    ) from exc

  if isinstance(search, Playlist) and len(search.tracks) == 0:
    raise LavalinkSearchError(query, reason='Playlist is empty')
  if (isinstance(search, list) and len(search) == 0) or search is None:
    raise LavalinkSearchError(query, reason='No results found')

  search_results = search if isinstance(search, list) else search.tracks
  if auto_filter:
    results = filter_results(query, search_results)
  else:
    results = [parse_result(result) for result in search_results]

  # Are there valid results?
  if len(results) == 0:
    raise LavalinkSearchError(query, reason='No valid results found')

  # Sort by descending similarity
  if desired_duration_ms is not None:
    results.sort(
      key=lambda x: (
        1 - check_similarity(query, x.title),
        abs(x.duration_ms - desired_duration_ms),
      )
    )
  else:
    results.sort(key=lambda x: 1 - check_similarity(query, x.title))

  return results
