"""
Dataclasses for storing authentication data for Discord, Last.fm, Spotify, etc.
"""
from dataclasses import dataclass


@dataclass
class OAuth:
    """
    Dataclass for storing authentication data for Discord, Spotify, etc.
    """
    user_id: int
    username: str
    access_token: str
    refresh_token: str
    expires_at: int


@dataclass
class LastfmAuth:
    """
    Dataclass for storing authentication data for Last.fm.
    """
    user_id: int
    username: str
    session_key: str
