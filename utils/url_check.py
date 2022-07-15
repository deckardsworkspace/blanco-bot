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
