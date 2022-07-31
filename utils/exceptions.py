class EndOfQueueError(Exception):
    pass

class SpotifyInvalidURLError(Exception):
    def __init__(self, url):
        self.message = "Invalid Spotify link or URI: {}".format(url)
        super().__init__(self.message)


class VoiceCommandError(Exception):
    def __init__(self, reason):
        self.message = reason
        super().__init__(self.message)


class YouTubeSearchError(Exception):
    def __init__(self, query, reason=None):
        self.message = f'Could not search for "{query}" on YouTube. Reason: {reason}'
        super().__init__(self.message)


class YouTubeInvalidURLError(Exception):
    def __init__(self, url, reason=None):
        self.message = f'Invalid YouTube video: {url}. Reason: {reason}'
        super().__init__(self.message)


class YouTubeInvalidPlaylistError(Exception):
    def __init__(self, url, reason=None):
        self.message = f'Invalid YouTube playlist: {url}. Reason: {reason}'
        super().__init__(self.message)
