"""
Dataclass for storing a Spotify track entity.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SpotifyTrack:
    """
    Dataclass for storing a Spotify track entity.
    """
    title: str
    artist: str       # First artist
    author: str       # All artists, separated by ', '
    spotify_id: str
    duration_ms: int
    artwork: Optional[str] = None
    isrc: Optional[str] = None
