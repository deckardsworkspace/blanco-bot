from base64 import b64encode
from dataclass.oauth import OAuth
from time import time
from typing import Dict, TYPE_CHECKING
from .constants import SPOTIFY_ACCOUNTS_BASE_URL, SPOTIFY_API_BASE_URL, USER_AGENT
from .logger import create_logger
import requests
if TYPE_CHECKING:
    from database import Database
    from dataclass.config import Config


class PrivateSpotify:
    """
    Custom Spotify client designed to work with predefined credentials
    obtained using the Authorization Code Flow. Used for instances where
    the user has already authorized the application and wants to access
    their data through Blanco.
    """
    def __init__(self, config: 'Config', db: 'Database', credentials: 'OAuth'):
        self._client_id = config.spotify_client_id
        self._client_secret = config.spotify_client_secret
        self._credentials = credentials
        self._db = db
        self._logger = create_logger(self.__class__.__name__, debug=config.debug_enabled)
    
    def _refresh_token(self):
        """
        Refresh the access token for a user.
        """
        response = requests.post(
            str(SPOTIFY_ACCOUNTS_BASE_URL / 'token'),
            headers={
                'Authorization': f'Basic {b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()}',
            },
            data={
                'grant_type': 'refresh_token',
                'refresh_token': self._credentials.refresh_token
            }
        )

        try:
            response.raise_for_status()
        except Exception as e:
            self._logger.error(f'Error refreshing Spotify access token for user {self._credentials.user_id}: {e}')

            # Delete the user's credentials from the database
            self._db.delete_oauth('spotify', self._credentials.user_id)
            raise

        # Update the credentials
        parsed = response.json()
        new_credentials = OAuth(
            user_id=self._credentials.user_id,
            username=self._credentials.username,
            access_token=parsed['access_token'],
            refresh_token=self._credentials.refresh_token,
            expires_at=int(time() + parsed['expires_in'])
        )
        self._db.set_oauth('spotify', new_credentials)
        self._db.set_spotify_scopes(self._credentials.user_id, parsed['scope'].split(' '))
        self._credentials = new_credentials

    def _ensure_auth(self):
        """
        Makes sure that the credentials are up to date.
        """
        if self._credentials.expires_at < time() + 60:
            # Refresh token
            self._logger.debug(f'Refreshing Spotify access token for user {self._credentials.user_id}')
            self._refresh_token()
    
    def get_user_playlists(self) -> Dict[str, str]:
        """
        Gets a list of 25 of the user's playlists.
        """
        self._ensure_auth()
        response = requests.get(
            str(SPOTIFY_API_BASE_URL / 'me' / 'playlists'),
            headers={
                'Authorization': f'Bearer {self._credentials.access_token}',
                'User-Agent': USER_AGENT
            },
            params={
                'limit': 25
            }
        )

        try:
            response.raise_for_status()
        except Exception as e:
            self._logger.error(f'Error getting Spotify playlists for user {self._credentials.user_id}: {e}')
            return {}
        
        parsed = response.json()
        return {
            playlist['id']: f'{playlist["name"]} ({playlist["tracks"]["total"]} tracks)' # type: ignore
            for playlist in parsed['items']
        }
    
    def save_track(self, spotify_id: str):
        """
        Adds a track to the user's Liked Songs.
        """
        self._ensure_auth()
        response = requests.put(
            str(SPOTIFY_API_BASE_URL / 'me' / 'tracks'),
            headers={
                'Authorization': f'Bearer {self._credentials.access_token}',
                'User-Agent': USER_AGENT
            },
            params={
                'ids': spotify_id
            }
        )

        try:
            response.raise_for_status()
        except Exception as e:
            self._logger.error(f'Could not like track {spotify_id}: {e}')
            raise
