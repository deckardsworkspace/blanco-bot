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

    # Get title and artist
    def get_details(self) -> Tuple[str, str]:
        if self.title is not None:
            title = self.title
            if self.artist is not None:
                artist = f'by {self.artist}'
            else:
                artist = 'by Unknown artist'
        elif self.url is not None:
            title = self.url
            artist = 'Direct link'
        else:
            title = self.query.replace('ytsearch:', '')
            artist = 'Search query'
        
        return title, artist