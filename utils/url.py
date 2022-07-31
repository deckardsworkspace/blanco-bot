from urllib.parse import urlparse, parse_qs
from .exceptions import LavalinkInvalidIdentifierError, SpotifyInvalidURLError
import re
import validators


def check_url(url: str) -> bool:
    return validators.domain(url) or validators.url(url)


def check_sc_url(url: str) -> bool:
    url_regex = r"(^http(s)?://)?(soundcloud\.com|snd\.sc)/(.*)$"
    return re.match(url_regex, url) is not None


def check_spotify_url(url: str) -> bool:
    url_regex = r"(https?://open\.)*spotify(\.com)*[/:]+(track|artist|album|playlist)[/:]+[A-Za-z0-9]+"
    return re.match(url_regex, url) is not None


def check_twitch_url(url: str) -> bool:
    url_regex = r"(^http(s)?://)?((www|en-es|en-gb|secure|beta|ro|www-origin|en-ca|fr-ca|lt|zh-tw|he|id|ca|mk|lv|ma|tl|hi|ar|bg|vi|th)\.)?twitch.tv/(?!directory|p|user/legal|admin|login|signup|jobs)(?P<channel>\w+)"
    return re.match(url_regex, url) is not None


def check_youtube_url(url: str) -> bool:
    url_regex = r"(?:https?://)?(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|/))([a-zA-Z0-9_-]+)"
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
        raise LavalinkInvalidIdentifierError(url, reason='SoundCloud URL does not point to a track or set.')
    elif len(path) == 2 and path[1] != 'sets':
        return True
    elif path[1] == 'sets':
        return False
    else:
        raise LavalinkInvalidIdentifierError(url, reason='Unrecognized SoundCloud URL.')


def get_spinfo_from_url(url: str, valid_types: list[str] = ["track", "album", "artist", "playlist"]) -> tuple[str, str]:
    if not check_spotify_url(url):
        raise SpotifyInvalidURLError(url)

    parsed_path = []
    if re.match(r"^https?://open\.spotify\.com", url):
        # We are dealing with a link
        parsed_url = urlparse(url)
        parsed_path = parsed_url.path.split("/")[1:]
    elif re.match(r"^spotify:[a-z]", url):
        # We are dealing with a Spotify URI
        parsed_path = url.split(":")[1:]
    if len(parsed_path) < 2 or parsed_path[0] not in valid_types:
        raise SpotifyInvalidURLError(url)

    return parsed_path[0], parsed_path[1]


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
