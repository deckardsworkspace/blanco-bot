"""
Wrapper for the spotipy Spotify client which supports pagination by default.
"""

from typing import Any, Dict, List, Optional, Tuple

from requests.exceptions import ConnectionError
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_fixed, wait_random)

import spotipy

from dataclass.spotify import SpotifyResult, SpotifyTrack
from database.redis import REDIS

from .exceptions import SpotifyInvalidURLError, SpotifyNoResultsError
from .time import human_readable_time


def extract_track_info(
    track_obj: Dict[str, Any],
    artwork: Optional[str] = None,
    album_name: Optional[str] = None
) -> SpotifyTrack:
    """
    Extracts track information from the Spotify API and returns a SpotifyTrack object.
    """
    if 'track' in track_obj.keys():
        # Nested track (playlist track object)
        track_obj = track_obj['track']

    # Extract ISRC if present
    isrc = None
    if 'external_ids' in track_obj.keys():
        if 'isrc' in track_obj['external_ids'].keys():
            isrc = track_obj['external_ids']['isrc'].upper().replace('-', '')

    # Extract album artwork if present
    if 'album' in track_obj.keys():
        album_name = track_obj['album']['name']
        if 'images' in track_obj['album'].keys():
            if len(track_obj['album']['images']) > 0:
                artwork = track_obj['album']['images'][0]['url']

    return SpotifyTrack(
        title=track_obj['name'],
        artist=track_obj['artists'][0]['name'],
        author=', '.join([x['name'] for x in track_obj['artists']]),
        album=album_name,
        spotify_id=track_obj['id'],
        duration_ms=int(track_obj['duration_ms']),
        artwork=artwork,
        isrc=isrc
    )


class Spotify:
    """
    Wrapper for the spotipy Spotify client which supports pagination by default.
    """
    def __init__(self, client_id: str, client_secret: str):
        self._client = spotipy.Spotify(
            auth_manager=spotipy.oauth2.SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
        )

    @property
    def client(self):
        """
        Returns the internal spotipy client.
        """
        return self._client

    def __get_art(self, art: List[Dict[str, str]], default='') -> str:
        """
        Returns the first image URL from a list of artwork images,
        or a specified default if the list is empty.
        """
        if len(art) == 0:
            return default
        return art[0]['url']

    def get_artist_top_tracks(self, artist_id: str) -> List[SpotifyTrack]:
        """
        Returns a list of SpotifyTrack objects for a given artist's
        top 10 tracks.
        """
        response = self._client.artist_top_tracks(artist_id)
        if response is None:
            raise SpotifyInvalidURLError(f'spotify:artist:{artist_id}')

        return [extract_track_info(track) for track in response['tracks']]

    def get_track_art(self, track_id: str) -> str:
        """
        Returns the track artwork for a given track ID.
        """
        result = self._client.track(track_id)
        if result is None:
            raise SpotifyInvalidURLError(f'spotify:track:{track_id}')
        return self.__get_art(result['album']['images'])

    def get_track(self, track_id: str) -> SpotifyTrack:
        """
        Returns a SpotifyTrack object for a given track ID.
        """
        # Check cache
        if REDIS is not None:
            cached_track = REDIS.get_spotify_track(track_id)
            if cached_track is not None:
                return cached_track

        result = self._client.track(track_id)
        if result is None:
            raise SpotifyInvalidURLError(f'spotify:track:{track_id}')

        # Save to cache
        if REDIS is not None:
            REDIS.set_spotify_track(track_id, extract_track_info(result))

        return extract_track_info(result)

    def get_tracks(self, list_type: str, list_id: str) -> Tuple[str, str, List[SpotifyTrack]]:
        """
        Returns a list of SpotifyTrack objects for a given album or playlist ID.
        May take a long time to complete if the list is large.
        """
        offset = 0
        tracks = []

        # Get list name and author
        list_artwork = None
        if list_type == 'album':
            album_info = self._client.album(list_id)
            if album_info is None:
                raise SpotifyInvalidURLError(f'spotify:{list_type}:{list_id}')

            list_artwork = album_info['images'][0]['url']
            list_name = album_info['name']
            list_author = album_info['artists'][0]['name']
        elif list_type == 'playlist':
            playlist_info = self._client.playlist(list_id, fields='name,owner.display_name')
            if playlist_info is None:
                raise SpotifyInvalidURLError(f'spotify:{list_type}:{list_id}')

            list_name = playlist_info['name']
            list_author = playlist_info['owner']['display_name']
        else:
            raise SpotifyInvalidURLError(f'spotify:{list_type}:{list_id}')

        # Get tracks
        while True:
            if list_type == 'album':
                response = self._client.album_tracks(list_id, offset=offset)
            else:
                fields = ','.join([
                    'items.track.name',
                    'items.track.artists',
                    'items.track.album',
                    'items.track.id',
                    'items.track.duration_ms',
                    'items.track.external_ids.isrc'
                ])
                response = self._client.playlist_items(list_id, offset=offset,
                                                      fields=fields,
                                                      additional_types=['track'])

            if response is None:
                raise SpotifyInvalidURLError(f'spotify:{list_type}:{list_id}')
            if len(response['items']) == 0:
                break

            tracks.extend(response['items'])
            offset = offset + len(response['items'])

        if list_type == 'playlist':
            return list_name, list_author, [
                extract_track_info(x)
                for x in tracks if x['track'] is not None
            ]
        return list_name, list_author, [
            extract_track_info(x, list_artwork, album_name=list_name)
            for x in tracks
        ]

    def search_track(self, query, limit: int = 1) -> List[SpotifyTrack]:
        """
        Searches Spotify for a given query and returns a list of SpotifyTrack objects.
        """
        response = self._client.search(query, limit=limit, type='track')
        if response is None or len(response['tracks']['items']) == 0:
            raise SpotifyNoResultsError

        return [extract_track_info(track) for track in response['tracks']['items']]

    @retry(
        retry=retry_if_exception_type(ConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1) + wait_random(0, 2)
    )
    def search(self, query: str, search_type: str) -> List[SpotifyResult]:
        """
        Searches Spotify for a given artist, album, or playlist,
        and returns a list of SpotifyResult objects.

        If you want to search for tracks specifically, use search_track(),
        as that will yield a list of SpotifyTrack objects instead of SpotifyResults.

        :param query: The artist/album/playlist to search for.
        :param search_type: The type of entity to search for.
            Must be one of 'artist', 'album', 'playlist', or 'track'.
        """
        if search_type not in ('artist', 'album', 'playlist', 'track'):
            raise ValueError(f'Invalid search type: {search_type}')

        response = self._client.search(query, limit=10, type=search_type)
        if response is None or len(response[f'{search_type}s']['items']) == 0:
            raise SpotifyNoResultsError

        # Parse results
        items = response[f'{search_type}s']['items']
        if search_type == 'artist':
            # Sort artists by followers
            items = sorted(items, key=lambda x: x['followers']['total'], reverse=True)
            results = [SpotifyResult(
                name=entity['name'],
                description=f'{entity["followers"]["total"]} followers',
                spotify_id=entity['id']
            ) for entity in items]
        elif search_type == 'album':
            # Include artist name, track count, and release date in album results
            results = [SpotifyResult(
                name=entity['name'],
                description=f'{entity["artists"][0]["name"]} '
                            f'({entity["total_tracks"]} tracks, '
                            f'released {entity["release_date"]})',
                spotify_id=entity['id']
            ) for entity in items]
        elif search_type == 'playlist':
            # Include author name and track count in playlist results
            results = [SpotifyResult(
                name=entity['name'],
                description=f'{entity["owner"]["display_name"]} '
                            f'({entity["tracks"]["total"]} tracks)',
                spotify_id=entity['id']
            ) for entity in items]
        else:
            # Include artist name and release date in track results
            results = [SpotifyResult(
                name=f'{entity["name"]} '
                     f'({human_readable_time(entity["duration_ms"])})',
                description=f'{entity["artists"][0]["name"]} - '
                            f'{entity["album"]["name"]} ',
                spotify_id=entity['id']
            ) for entity in items]

        return results
