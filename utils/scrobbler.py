from datetime import datetime
from time import mktime
from typing import TYPE_CHECKING
import pylast
if TYPE_CHECKING:
    from dataclass.config import Config
    from dataclass.queue_item import QueueItem
    from dataclass.oauth import LastfmAuth


class Scrobbler:
    """
    Scrobbler class for scrobbling songs to Last.fm.
    Meant for single use, i.e., one instance per user per listening session.
    """
    def __init__(self, config: 'Config', creds: 'LastfmAuth'):
        if config.lastfm_api_key is None or config.lastfm_shared_secret is None:
            raise ValueError('Last.fm API key and/or shared secret not set.')
        
        # Create Network object
        self._net = pylast.LastFMNetwork(
            api_key=config.lastfm_api_key,
            api_secret=config.lastfm_shared_secret
        )
        
        # Set session key
        self._net.session_key = creds.session_key
    
    def scrobble(self, track: 'QueueItem'):
        timestamp = track.start_time
        if timestamp is None:
            timestamp = int(mktime(datetime.now().timetuple()))
        
        duration = None
        if track.duration is not None:
            duration = track.duration // 1000
        
        self._net.scrobble(
            artist=track.artist,
            title=track.title,
            timestamp=timestamp,
            duration=duration
        )
