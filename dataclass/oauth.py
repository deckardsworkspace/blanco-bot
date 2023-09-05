from dataclasses import dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class OAuth:
    user_id: int
    username: str
    access_token: str
    refresh_token: str
    expires_at: 'datetime'


@dataclass
class LastfmAuth:
    user_id: int
    username: str
    session_key: str
