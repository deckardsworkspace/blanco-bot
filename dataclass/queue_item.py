from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class QueueItem:
    # Who requested the track (required)
    requester: int

    # The Spotify ID for the track, if any
    spotify_id: Optional[str] = None

    # Direct track URL
    url: Optional[str] = None

    # Track details
    title: Optional[str] = None
    artist: Optional[str] = None
    duration: Optional[int] = 0   # milliseconds
    lavalink_track: Optional[str] = None

    # Get title and artist
    def get_details(self) -> Tuple[str, str]:
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