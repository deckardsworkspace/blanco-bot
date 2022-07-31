from dataclasses import dataclass


@dataclass
class YouTubeResult:
    title: str
    author: str
    duration_ms: int
    url: str
    lavalink_track: str
