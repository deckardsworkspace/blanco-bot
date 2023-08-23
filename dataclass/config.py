from dataclasses import dataclass, field
from typing import List


@dataclass
class LavalinkNode:
    id: str
    password: str
    host: str
    port: int
    regions: List[str]
    secure: bool = False

    # Type checking
    def __post_init__(self):
        # Check if host, password, and label are strings
        if not isinstance(self.host, str):
            raise TypeError('server must be a string')
        if not isinstance(self.password, str):
            raise TypeError('password must be a string')
        if not isinstance(self.id, str):
            raise TypeError('id must be a string')
        
        # Check if port is an int
        if not isinstance(self.port, int):
            raise TypeError('port must be an int')
        
        # Check if ssl is a bool
        if not isinstance(self.secure, bool):
            raise TypeError('ssl must be a bool')

        # Check if regions is a list
        if not isinstance(self.regions, list):
            raise TypeError('regions must be a list')


@dataclass
class Config:
    # Required
    db_file: str
    discord_token: str
    spotify_client_id: str
    spotify_client_secret: str
    lavalink_nodes: List[LavalinkNode]

    # Optional
    debug_enabled: bool = False
    debug_guild_ids: List[int] = field(default_factory=list)
