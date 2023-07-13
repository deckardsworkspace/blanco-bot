from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from mafic import Track


@dataclass
class LavalinkResult:
    title: str
    author: str
    duration_ms: int
    lavalink_track: 'Track'
    url: Optional[str] = None
