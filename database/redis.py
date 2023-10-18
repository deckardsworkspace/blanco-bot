"""
Redis client that takes care of caching MusicBrainz and Spotify lookups.
"""

from typing import Optional

import redis

from dataclass.spotify import SpotifyTrack
from utils.config import REDIS_HOST, REDIS_PASSWORD, REDIS_PORT
from utils.logger import create_logger


class RedisClient:
    """
    Redis client that takes care of caching MusicBrainz and Spotify lookups.
    """
    def __init__(self, host: str, port: int, password: Optional[str] = None):
        self._client = redis.StrictRedis(
            host=host,
            port=port,
            password=password,
            encoding='utf-8',
            decode_responses=True
        )

        # Logger
        self._logger = create_logger(self.__class__.__name__)
        self._logger.debug('Attempting to connect to Redis server...')

        # Test connection
        try:
            self._client.ping()
        except redis.ConnectionError as err:
            self._logger.critical('Could not connect to Redis server. Check your configuration.')
            raise RuntimeError('Could not connect to Redis server.') from err

        self._logger.info('Connected to Redis server. Enable debug logging to see cache hits.')

    def set_lavalink_track(self, key: str, value: str, *, key_type: str):
        """
        Save an encoded Lavalink track.

        :param key: The key to save the track under.
        :param value: The encoded track.
        :param key_type: The type of key to save the track under, e.g. 'isrc' or 'spotify_id'.
        """
        self._logger.debug('Caching Lavalink track for %s:%s', key_type, key)
        self._client.set(f'lavalink:{key_type}:{key}', value)

    def get_lavalink_track(self, key: str, *, key_type: str) -> Optional[str]:
        """
        Get an encoded Lavalink track.

        :param key: The key to get the track from.
        :param key_type: The type of key to get the track from, e.g. 'isrc' or 'spotify_id'.
        """
        if not self._client.exists(f'lavalink:{key_type}:{key}'):
            return None

        self._logger.debug('Got cached Lavalink track for %s:%s', key_type, key)
        return self._client.get(f'lavalink:{key_type}:{key}') # type: ignore

    def invalidate_lavalink_track(self, key: str, *, key_type: str):
        """
        Removes a cached Lavalink track.
        
        :param key: The key to remove the track for.
        :param key_type: The type of key to remove the track for, e.g. 'isrc' or 'spotify_id'.
        """
        self._logger.debug('Invalidating Lavalink track for %s:%s', key_type, key)
        if self._client.exists(f'lavalink:{key_type}:{key}'):
            self._client.delete(f'lavalink:{key_type}:{key}')

    def set_spotify_track(self, spotify_id: str, track: 'SpotifyTrack'):
        """
        Save a Spotify track.
        """
        self._logger.debug('Caching info for Spotify track %s', spotify_id)
        self._client.hmset(f'spotify:{spotify_id}', {
            'title': track.title,
            'artist': track.artist,
            'author': track.author,
            'duration_ms': track.duration_ms,
            'artwork': track.artwork if track.artwork is not None else '',
            'album': track.album if track.album is not None else '',
            'isrc': track.isrc if track.isrc is not None else '',
        })

        # Remove standalone ISRC cache
        if self._client.exists(f'isrc:{spotify_id}'):
            self._client.delete(f'isrc:{spotify_id}')

    def get_spotify_track(self, spotify_id: str) -> Optional['SpotifyTrack']:
        """
        Get a Spotify track.
        """
        track = self._client.hgetall(f'spotify:{spotify_id}')

        if not track:
            return None

        self._logger.debug('Got cached info for Spotify track %s', spotify_id)
        return SpotifyTrack(
            title=track['title'], # type: ignore
            artist=track['artist'], # type: ignore
            author=track['author'], # type: ignore
            duration_ms=int(track['duration_ms']), # type: ignore
            artwork=track['artwork'] if track['artwork'] else None, # type: ignore
            album=track['album'] if track['album'] else None, # type: ignore
            isrc=track['isrc'] if track['isrc'] else None, # type: ignore
            spotify_id=spotify_id
        )

    def set_mbid(self, spotify_id: str, mbid: str):
        """
        Save a MusicBrainz ID for a Spotify track.
        """
        self._logger.debug('Caching MusicBrainz ID for Spotify track %s', spotify_id)
        self._client.set(f'mbid:{spotify_id}', mbid)

    def get_mbid(self, spotify_id: str) -> Optional[str]:
        """
        Get a MusicBrainz ID for a Spotify track.
        """
        if not self._client.exists(f'mbid:{spotify_id}'):
            return None

        self._logger.debug('Got cached MusicBrainz ID for Spotify track %s', spotify_id)
        return self._client.get(f'mbid:{spotify_id}') # type: ignore

    def set_isrc(self, spotify_id: str, isrc: str):
        """
        Save an ISRC for a Spotify track.
        """
        # Check if there is a Spotify track with this ID
        if self._client.exists(f'spotify:{spotify_id}'):
            # Update ISRC in Spotify track
            self._logger.debug('Updating cached ISRC for Spotify track %s', spotify_id)
            self._client.hset(f'spotify:{spotify_id}', 'isrc', isrc)

        self._logger.debug('Caching ISRC for Spotify track %s', spotify_id)
        self._client.set(f'isrc:{spotify_id}', isrc)

    def get_isrc(self, spotify_id: str) -> Optional[str]:
        """
        Get an ISRC for a Spotify track.
        """
        # Check if there is a Spotify track with this ID
        if self._client.exists(f'spotify:{spotify_id}'):
            # Return ISRC from Spotify track
            self._logger.debug('Got cached ISRC for Spotify track %s', spotify_id)
            return self._client.hget(f'spotify:{spotify_id}', 'isrc') # type: ignore

        if not self._client.exists(f'isrc:{spotify_id}'):
            return None

        self._logger.debug('Got cached ISRC for Spotify track %s', spotify_id)
        return self._client.get(f'isrc:{spotify_id}') # type: ignore


REDIS = None
if REDIS_HOST is not None and REDIS_PORT != -1:
    REDIS = RedisClient(REDIS_HOST, REDIS_PORT, REDIS_PASSWORD)
