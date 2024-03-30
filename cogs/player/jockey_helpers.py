"""
Helper functions for the music player.
"""

from typing import TYPE_CHECKING, List, Tuple, TypeVar

from mafic import SearchType
from requests.status_codes import codes
from spotipy.exceptions import SpotifyException

from database.redis import REDIS
from dataclass.queue_item import QueueItem
from utils.constants import CONFIDENCE_THRESHOLD
from utils.exceptions import (
  JockeyException,
  LavalinkInvalidIdentifierError,
  SpotifyNoResultsError,
)
from utils.fuzzy import check_similarity_weighted
from utils.logger import create_logger
from utils.spotify_client import Spotify
from utils.url import (
  check_sc_url,
  check_spotify_url,
  check_url,
  check_youtube_playlist_url,
  check_youtube_url,
  check_ytmusic_playlist_url,
  check_ytmusic_url,
  get_spinfo_from_url,
  get_ytid_from_url,
  get_ytlistid_from_url,
)

from .lavalink_client import (
  get_soundcloud_matches,
  get_youtube_matches,
)

if TYPE_CHECKING:
  from mafic import Node

  from dataclass.spotify import SpotifyTrack


LOGGER = create_logger('jockey_helpers')
T = TypeVar('T')


def rank_results(
  query: str, results: List[T], result_type: SearchType
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
      int(100 * (0.8**i)),
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
      '  %3d  %-20s  %-25s',
      confidence,
      result.author[:20],  # type: ignore
      result.title[:25],  # type: ignore
    )

  return ranked


def invalidate_lavalink_track(item: QueueItem):
  """
  Removes a cached Lavalink track from Redis.

  :param item: The QueueItem to invalidate the track for.
  """
  if REDIS is None:
    return

  # Determine key type
  redis_key = None
  redis_key_type = None
  if item.spotify_id is not None:
    redis_key = item.spotify_id
    redis_key_type = 'spotify_id'
  elif item.isrc is not None:
    redis_key = item.isrc
    redis_key_type = 'isrc'

  # Invalidate cached Lavalink track
  if redis_key is not None and redis_key_type is not None:
    REDIS.invalidate_lavalink_track(redis_key, key_type=redis_key_type)
  else:
    LOGGER.warning("Could not invalidate cached track for `%s': no key", item.title)


async def parse_query(
  node: 'Node', spotify: Spotify, query: str, requester: int
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
    results = spotify.search_track(query, limit=10)
  except SpotifyNoResultsError:
    pass
  else:
    # Return top result if it's good enough
    ranked = rank_results(query, results, SearchType.SPOTIFY_SEARCH)
    if ranked[0][1] >= CONFIDENCE_THRESHOLD:
      track = ranked[0][0]
      return [
        QueueItem(
          requester=requester,
          title=track.title,
          artist=track.artist,
          author=track.author,
          album=track.album,
          spotify_id=track.spotify_id,
          duration=track.duration_ms,
          artwork=track.artwork,
          isrc=track.isrc,
        )
      ]

  # Get matching tracks from YouTube
  results = await get_youtube_matches(node, query, auto_filter=False)

  # Return top result
  ranked = rank_results(query, results, SearchType.YOUTUBE)
  result = ranked[0][0]
  return [
    QueueItem(
      title=result.title,
      artist=result.author,
      artwork=result.artwork_url,
      duration=result.duration_ms,
      requester=requester,
      url=result.url,
      lavalink_track=result.lavalink_track,
    )
  ]


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

  return [
    QueueItem(
      requester=requester,
      title=track.title,
      artist=track.author,
      artwork=track.artwork_url,
      duration=track.duration_ms,
      url=track.url,
      lavalink_track=track.lavalink_track,
    )
    for track in tracks
  ]


async def parse_spotify_query(
  spotify: Spotify, query: str, requester: int
) -> List[QueueItem]:
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
    elif sp_type == 'artist':
      # Get top tracks from Spotify
      track_queue = spotify.get_artist_top_tracks(sp_id)
    else:
      # Get playlist or album tracks from Spotify
      track_queue = spotify.get_tracks(sp_type, sp_id)[2]
  except SpotifyException as exc:
    if exc.http_status == codes.not_found:
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
    raise SpotifyNoResultsError(f'{sp_type} does not have any public tracks.')

  # At least one track.
  for track in track_queue:
    new_tracks.append(
      QueueItem(
        requester=requester,
        title=track.title,
        artist=track.artist,
        author=track.author,
        album=track.album,
        spotify_id=track.spotify_id,
        duration=track.duration_ms,
        artwork=track.artwork,
        isrc=track.isrc,
      )
    )

  return new_tracks


async def parse_youtube_playlist(
  node: 'Node', query: str, requester: int
) -> List[QueueItem]:
  """
  Parse a YouTube playlist query and return a list of QueueItems.
  See parse_query() for more information.
  """
  try:
    # Get playlist tracks from YouTube
    playlist_id = get_ytlistid_from_url(query)
    tracks = await get_youtube_matches(
      node, f'https://youtube.com/playlist?list={playlist_id}'
    )
  except Exception as exc:
    # No tracks.
    raise LavalinkInvalidIdentifierError(
      query, 'Playlist is empty, private, or nonexistent'
    ) from exc

  return [
    QueueItem(
      requester=requester,
      title=track.title,
      artist=track.author,
      artwork=track.artwork_url,
      duration=track.duration_ms,
      url=track.url,
      lavalink_track=track.lavalink_track,
    )
    for track in tracks
  ]


async def parse_youtube_query(
  node: 'Node', query: str, requester: int
) -> List[QueueItem]:
  """
  Parse a non-playlist YouTube query and return a list of QueueItems.
  See parse_query() for more information.
  """
  # Is it a video?
  try:
    video_id = get_ytid_from_url(query)

    # Get the video's details
    video = await get_youtube_matches(node, video_id)
    return [
      QueueItem(
        title=video[0].title,
        artist=video[0].author,
        artwork=video[0].artwork_url,
        requester=requester,
        duration=video[0].duration_ms,
        url=video[0].url,
        lavalink_track=video[0].lavalink_track,
      )
    ]
  except LavalinkInvalidIdentifierError:
    raise
  except Exception as exc:
    raise LavalinkInvalidIdentifierError(
      query, 'Only YouTube video and playlist URLs are supported.'
    ) from exc
