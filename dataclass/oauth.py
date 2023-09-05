from dataclasses import dataclass


@dataclass
class OAuth:
    user_id: int
    username: str
    access_token: str
    refresh_token: str
    expires_at: int


@dataclass
class LastfmAuth:
    user_id: int
    username: str
    session_key: str
