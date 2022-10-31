from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from lavalink.models import AudioTrack


@dataclass
class LavalinkResult:
    title: str
    author: str
    duration_ms: int
    url: str
    lavalink_track: 'AudioTrack'
