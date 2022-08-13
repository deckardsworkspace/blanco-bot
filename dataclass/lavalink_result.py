from dataclasses import dataclass
from typing import Dict


@dataclass
class LavalinkResult:
    title: str
    author: str
    duration_ms: int
    url: str
    lavalink_track: Dict[str, any]
