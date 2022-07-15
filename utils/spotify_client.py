from os import environ
from typing import Dict, List, Tuple
from urllib.parse import urlparse
from .exceptions import SpotifyInvalidURLError
from .url_check import check_spotify_url
import re
import spotipy


def get_chunks(lst):
    # Spotify only allows adding up to 100 tracks at once,
    # so we have to split particularly large playlists into
    # multiple requests.
    for i in range(0, len(lst), 100):
        yield lst[i:i + 100]


def extract_track_info(track_obj) -> Tuple[str, str, str, int]:
    if 'track' in track_obj:
        # Nested track (playlist track object)
        track_obj = track_obj['track']
    return (
        track_obj['name'],
        track_obj['artists'][0]['name'],
        track_obj['id'],
        int(track_obj['duration_ms'])
    )


def parse_spotify_url(url: str, valid_types: list[str] = ["track", "album", "artist", "playlist"]) -> tuple[str, str]:
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


class Spotify:
    def __init__(self):
        self._client = spotipy.Spotify(
            auth_manager=spotipy.oauth2.SpotifyClientCredentials(
                client_id=environ['SPOTIFY_ID'],
                client_secret=environ['SPOTIFY_SECRET']
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
        return self.__get_art(self._client.album(album_id)['images'])
    
    def get_artist_image(self, artist_id: str) -> str:
        return self.__get_art(self._client.artist(artist_id)['images'])

    def get_playlist_cover(self, playlist_id: str, default: str) -> str:
        return self.__get_art(self._client.playlist_cover_image(playlist_id), default=default)

    def get_track_art(self, track_id: str) -> str:
        return self.__get_art(self._client.track(track_id)['album']['images'])

    def get_track(self, track_id: str) -> Tuple[str, str]:
        return extract_track_info(self._client.track(track_id))

    def get_tracks(self, list_type: str, list_id: str) -> Tuple[str, str, List[Tuple[str, str, str, int]]]:
        offset = 0
        tracks = []

        # Get list name and author
        if list_type == 'album':
            album_info = self._client.album(list_id)
            list_name = album_info['name']
            list_author = album_info['artists'][0]['name']
        elif list_type == 'playlist':
            playlist_info = self._client.playlist(list_id, fields='name,owner.display_name')
            list_name = playlist_info['name']
            list_author = playlist_info['owner']['display_name']
        else:
            raise SpotifyInvalidURLError(f'spotify:{list_type}:{list_id}')

        # Get tracks
        while True:
            if list_type == 'album':
                response = self._client.album_tracks(list_id, offset=offset)
            else:
                fields = 'items.track.name,items.track.artists,items.track.id,items.track.duration_ms'
                response = self._client.playlist_items(list_id, offset=offset,
                                                      fields=fields,
                                                      additional_types=['track'])

            if len(response['items']) == 0:
                break

            tracks.extend(response['items'])
            offset = offset + len(response['items'])

        return list_name, list_author, list(map(extract_track_info, tracks))
