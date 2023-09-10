"""
Wrapper for the spotipy Spotify client which supports pagination by default.
"""

from typing import Any, Dict, List, Optional, Tuple

import spotipy

from dataclass.spotify_track import SpotifyTrack

from .exceptions import SpotifyInvalidURLError, SpotifyNoResultsError


def extract_track_info(track_obj: Dict[str, Any], artwork: Optional[str] = None) -> SpotifyTrack:
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
            isrc = track_obj['external_ids']['isrc']

    # Extract album artwork if present
    if 'album' in track_obj.keys():
        if 'images' in track_obj['album'].keys():
            if len(track_obj['album']['images']) > 0:
                artwork = track_obj['album']['images'][0]['url']

    return SpotifyTrack(
        title=track_obj['name'],
        artist=track_obj['artists'][0]['name'],
        artists=', '.join([x['name'] for x in track_obj['artists']]),
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
        result = self._client.track(track_id)
        if result is None:
            raise SpotifyInvalidURLError(f'spotify:track:{track_id}')
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
                    'items.track.album.images',
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
        return list_name, list_author, [extract_track_info(x, list_artwork) for x in tracks]

    def search(self, query, limit: int = 1) -> List[SpotifyTrack]:
        """
        Searches Spotify for a given query and returns a list of SpotifyTrack objects.
        """
        response = self._client.search(query, limit=limit, type='track')
        if response is None or len(response['tracks']['items']) == 0:
            raise SpotifyNoResultsError

        return [extract_track_info(track) for track in response['tracks']['items']]
