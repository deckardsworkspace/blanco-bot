"""
String methods for validating and parsing URLs.
"""

import re
from urllib.parse import parse_qs, urlparse

import validators

from .exceptions import LavalinkInvalidIdentifierError, SpotifyInvalidURLError

MIN_SPOTIFY_URL_SEGMENTS = 2
NUM_SC_TRACK_URL_SEGMENTS = 2


def check_contains_ytlistid(url: str) -> bool:
  """
  Checks if the URL is a YouTube URL with a 'list' query parameter.
  """
  if not check_youtube_url(url):
    return False

  parsed_url = urlparse(url)
  query = parse_qs(parsed_url.query)
  return 'list' in query and len(query['list']) > 0


def check_url(url: str) -> bool:
  """
  Checks if the URL is a valid URL.
  """
  return validators.domain(url) or validators.url(url)  # type: ignore


def check_sc_url(url: str) -> bool:
  """
  Checks if the URL is a valid SoundCloud URL.
  """
  url_regex = r'(^http(s)?://)?(soundcloud\.com|snd\.sc)/(.*)$'
  return re.match(url_regex, url) is not None


def check_spotify_url(url: str) -> bool:
  """
  Checks if the URL is a valid Spotify URL.
  """
  url_regex = r'(https?://open\.)*spotify(\.com)*[/:]+(track|artist|album|playlist)[/:]+[A-Za-z0-9]+'  # pylint: disable=line-too-long
  return re.match(url_regex, url) is not None


def check_twitch_url(url: str) -> bool:
  """
  Checks if the URL is a valid Twitch URL.
  """
  url_regex = r'(^http(s)?://)?((www|en-es|en-gb|secure|beta|ro|www-origin|en-ca|fr-ca|lt|zh-tw|he|id|ca|mk|lv|ma|tl|hi|ar|bg|vi|th)\.)?twitch.tv/(?!directory|p|user/legal|admin|login|signup|jobs)(?P<channel>\w+)'  # pylint: disable=line-too-long
  return re.match(url_regex, url) is not None


def check_youtube_url(url: str) -> bool:
  """
  Checks if the URL is a valid YouTube URL.
  """
  url_regex = r'(?:https?://)?(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|/))([a-zA-Z0-9_-]+)'  # pylint: disable=line-too-long
  return re.match(url_regex, url) is not None


def check_youtube_playlist_url(url: str) -> bool:
  """
  Checks if the URL is a valid YouTube playlist URL.
  """
  url_regex = r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
  return re.match(url_regex, url) is not None


def check_ytmusic_url(url: str) -> bool:
  """
  Checks if the URL is a valid YouTube Music URL.
  """
  url_regex = r'(?:https?://)?music\.youtube\.com/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|/)([a-zA-Z0-9_-]+)'  # pylint: disable=line-too-long
  return re.match(url_regex, url) is not None


def check_ytmusic_playlist_url(url: str) -> bool:
  """
  Checks if the URL is a valid YouTube Music playlist URL.
  """
  url_regex = r'(?:https?://)?music\.youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
  return re.match(url_regex, url) is not None


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
    raise LavalinkInvalidIdentifierError(
      url, reason='SoundCloud URL does not point to a track or set.'
    )
  if len(path) == NUM_SC_TRACK_URL_SEGMENTS and path[1] != 'sets':
    return True
  if path[1] == 'sets':
    return False
  raise LavalinkInvalidIdentifierError(url, reason='Unrecognized SoundCloud URL.')


def get_spinfo_from_url(url: str) -> tuple[str, str]:
  """
  Gets the Spotify type and ID from a Spotify URL.
  Must be a URL that Blanco can play, i.e. a track, album, or playlist.

  :returns: A tuple containing the type and ID of the Spotify entity.
  """
  if not check_spotify_url(url):
    raise SpotifyInvalidURLError(url)

  parsed_path = []
  if re.match(r'^https?://open\.spotify\.com', url):
    # We are dealing with a link
    parsed_url = urlparse(url)
    parsed_path = parsed_url.path.split('/')[1:]
  elif re.match(r'^spotify:[a-z]', url):
    # We are dealing with a Spotify URI
    parsed_path = url.split(':')[1:]
  if len(parsed_path) < MIN_SPOTIFY_URL_SEGMENTS or parsed_path[0] not in (
    'track',
    'album',
    'playlist',
    'artist',
  ):
    raise SpotifyInvalidURLError(url)

  return parsed_path[0], parsed_path[1]


def get_ytid_from_url(url: str, id_type: str = 'v') -> str:
  """
  Gets the YouTube ID from a YouTube URL.
  """
  # https://gist.github.com/kmonsoor/2a1afba4ee127cce50a0
  if url.startswith(('youtu', 'www')):
    url = 'http://' + url

  query = urlparse(url)
  if query.hostname is None:
    raise LavalinkInvalidIdentifierError(url, reason='Not a valid YouTube URL')

  if 'youtube' in query.hostname:
    if re.match(r'^/watch', query.path):
      if len(query.query):
        return parse_qs(query.query)[id_type][0]
      return query.path.split('/')[2]
    if query.path.startswith(('/embed/', '/v/')):
      return query.path.split('/')[2]
  elif 'youtu.be' in query.hostname:
    return query.path[1:]

  raise LavalinkInvalidIdentifierError(
    url, reason='Could not get video ID from YouTube URL'
  )


def get_ytlistid_from_url(url: str, force_extract: bool = False) -> str:
  """
  Gets the YouTube playlist ID from a YouTube URL.
  """
  if url.startswith(('youtu', 'www')):
    url = 'http://' + url

  query = urlparse(url)
  if query.hostname is None:
    raise LavalinkInvalidIdentifierError(url, reason='Not a valid YouTube URL')

  if 'youtube' in query.hostname:
    if re.match(r'^/playlist', query.path) or force_extract:
      if len(query.query):
        return parse_qs(query.query)['list'][0]
    else:
      raise ValueError('Not a YouTube playlist URL')

  raise LavalinkInvalidIdentifierError(
    url, reason='Could not get playlist ID from YouTube URL'
  )
