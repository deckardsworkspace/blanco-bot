"""
Dataclass for storing Lavalink search results.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mafic import Track


@dataclass
class LavalinkResult:
    """
    Dataclass for storing Lavalink search results.
    """
    title: str
    author: str
    duration_ms: int
    lavalink_track: 'Track'
    artwork_url: Optional[str] = None
    url: Optional[str] = None
