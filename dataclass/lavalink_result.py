from dataclasses import dataclass


@dataclass
class LavalinkResult:
    title: str
    author: str
    duration_ms: int
    url: str
    lavalink_track: str
