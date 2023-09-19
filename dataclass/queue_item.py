"""
Dataclass for storing a track in the player queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from mafic import Track


@dataclass
class QueueItem:
    """
    Dataclass for storing a track in the player queue.
    """
    # Who requested the track (required)
    requester: int

    # The Spotify ID for the track, if any
    spotify_id: Optional[str] = None

    # The MusicBrainz ID for the track, if any
    mbid: Optional[str] = None

    # International Standard Recording Code (ISRC)
    isrc: Optional[str] = None

    # Direct track URL
    url: Optional[str] = None

    # Album artwork
    artwork: Optional[str] = None

    # Track details
    title: Optional[str] = None
    artist: Optional[str] = None # First artist
    author: Optional[str] = None # All artists, separated by ', '
    album: Optional[str] = None
    duration: Optional[int] = 0   # milliseconds
    lavalink_track: Optional['Track'] = None

    # Imperfect match - True when ISRC is present but no match found on YouTube
    is_imperfect: Optional[bool] = False

    # If annotate_track() was called on this track
    is_annotated: Optional[bool] = False

    # When the track started playing
    start_time: Optional[int] = None

    # Get title and artist
    def get_details(self) -> Tuple[str, str]:
        """
        Get a string of the form `title - artist` for the track.
        """
        if self.title is not None:
            title = self.title
            if self.artist is not None:
                artist = self.artist
            else:
                artist = 'Unknown artist'
        elif self.url is not None:
            title = self.url
            artist = '(direct link)'
        else:
            title = 'Unknown title'
            artist = 'Unknown query'

        return title, artist
