"""
Last.fm scrobbling client.
"""

from datetime import datetime
from time import mktime
from typing import TYPE_CHECKING

import pylast

if TYPE_CHECKING:
    from logging import Logger

    from dataclass.config import Config
    from dataclass.oauth import LastfmAuth
    from dataclass.queue_item import QueueItem


class Scrobbler:
    """
    Scrobbler class for scrobbling songs to Last.fm.
    Meant for single use, i.e., one instance per user per listening session.
    """
    def __init__(self, config: 'Config', creds: 'LastfmAuth', logger: 'Logger'):
        if config.lastfm_api_key is None or config.lastfm_shared_secret is None:
            raise ValueError('Last.fm API key and/or shared secret not set.')
        self._user_id = creds.user_id

        # Create Network object
        self._net = pylast.LastFMNetwork(
            api_key=config.lastfm_api_key,
            api_secret=config.lastfm_shared_secret
        )

        # Set session key
        self._net.session_key = creds.session_key

        # Logger
        self._logger = logger
        self._logger.debug('Created scrobbler for user %d', creds.user_id)

    def scrobble(self, track: 'QueueItem'):
        """
        Scrobbles a QueueItem from the music player.
        """
        timestamp = track.start_time
        if timestamp is None:
            timestamp = int(mktime(datetime.now().timetuple()))

        duration = None
        if track.duration is not None:
            duration = track.duration // 1000

        # Warn if MBID is not set
        if track.mbid is None:
            self._logger.warning(
                'MBID not set for track `%s\'; scrobble might not be accurate.',
                track.title
            )

        try:
            self._net.scrobble(
                artist=track.artist,
                title=track.title,
                timestamp=timestamp,
                duration=duration,
                mbid=track.mbid
            )
        except pylast.PyLastError as err:
            self._logger.error(
                'Error scrobbling `%s\' for user %d: %s',
                track.title,
                self._user_id,
                err
            )
            raise

        self._logger.debug(
            'Scrobbled `%s\' for user %d',
            track.title,
            self._user_id
        )
