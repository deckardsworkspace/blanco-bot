from dataclass.spotify_track import SpotifyTrack
from typing import Any, Dict, List, Optional, Tuple
from .exceptions import SpotifyInvalidURLError, SpotifyNoResultsError
import spotipy


def get_chunks(lst):
    # Spotify only allows adding up to 100 tracks at once,
    # so we have to split particularly large playlists into
    # multiple requests.
    for i in range(0, len(lst), 100):
        yield lst[i:i + 100]


def extract_track_info(track_obj: Dict[str, Any], artwork: Optional[str] = None) -> SpotifyTrack:
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
        spotify_id=track_obj['id'],
        duration_ms=int(track_obj['duration_ms']),
        artwork=artwork,
        isrc=isrc
    )


class Spotify:
    def __init__(self, client_id: str, client_secret: str):
        self._client = spotipy.Spotify(
            auth_manager=spotipy.oauth2.SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
        )

    @property
    def client(self):
        return self._client
    
    def __get_art(self, art: List[Dict[str, str]], default='') -> str:
        if not len(art):
            return default
        return art[0]['url']
    
    def get_album_art(self, album_id: str) -> str:
        result = self._client.album(album_id)
        if result is None:
            raise SpotifyInvalidURLError(f'spotify:album:{album_id}')
        return self.__get_art(result['images'])
    
    def get_artist_image(self, artist_id: str) -> str:
        result = self._client.artist(artist_id)
        if result is None:
            raise SpotifyInvalidURLError(f'spotify:artist:{artist_id}')
        return self.__get_art(result['images'])

    def get_playlist_cover(self, playlist_id: str, default: str) -> str:
        images = self._client.playlist_cover_image(playlist_id)
        if images is None:
            images = []
        return self.__get_art(images, default=default)

    def get_track_art(self, track_id: str) -> str:
        result = self._client.track(track_id)
        if result is None:
            raise SpotifyInvalidURLError(f'spotify:track:{track_id}')
        return self.__get_art(result['album']['images'])

    def get_track(self, track_id: str) -> SpotifyTrack:
        result = self._client.track(track_id)
        if result is None:
            raise SpotifyInvalidURLError(f'spotify:track:{track_id}')
        return extract_track_info(result)

    def get_tracks(self, list_type: str, list_id: str) -> Tuple[str, str, List[SpotifyTrack]]:
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
            return list_name, list_author, [extract_track_info(x) for x in tracks if x['track'] is not None]
        else:
            return list_name, list_author, [extract_track_info(x, list_artwork) for x in tracks]

    def search(self, query) -> SpotifyTrack:
        response = self._client.search(query, limit=1, type='track')
        if response is None or len(response['tracks']['items']) == 0:
            raise SpotifyNoResultsError()

        return extract_track_info(response['tracks']['items'][0])
