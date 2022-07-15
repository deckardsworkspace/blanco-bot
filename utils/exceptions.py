class YouTubeInvalidURLError(Exception):
    def __init__(self, url, reason=None):
        self.message = f'Invalid YouTube video: {url}. Reason: {reason}'
        super().__init__(self.message)


class YouTubeInvalidPlaylistError(Exception):
    def __init__(self, url, reason=None):
        self.message = f'Invalid YouTube playlist: {url}. Reason: {reason}'
        super().__init__(self.message)
