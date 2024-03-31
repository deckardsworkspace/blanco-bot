from datetime import UTC, datetime
from typing import TYPE_CHECKING, Dict, Optional
from uuid import uuid4

import jwt

from bot.api.models.session import Session
from bot.utils.config import config as bot_config
from bot.utils.logger import create_logger

if TYPE_CHECKING:
  from bot.database import Database
  from bot.models.oauth import OAuth

_MIN_IN_SECONDS = 60
SESSION_LIFETIME = 60 * _MIN_IN_SECONDS


class SessionManager:
  """
  Manages user sessions.
  """

  def __init__(self, database: 'Database'):
    self._database = database
    self._logger = create_logger('api.session')
    self._sessions: Dict[str, Session] = {}
    self._secret = bot_config.jwt_secret

  def create_session(self, user_id: int) -> str:
    """
    Create a new session.

    Returns:
      str: The session ID.
    """

    user: Optional['OAuth'] = self._database.get_oauth('discord', user_id)
    if user is None:
      raise ValueError('User not found')

    session_id = str(uuid4())
    expiration_time = int(datetime.now(tz=UTC).timestamp()) + SESSION_LIFETIME
    session = Session(
      session_id=session_id, user_id=user_id, expiration_time=expiration_time
    )
    self._sessions[session_id] = session

    return session_id

  def get_session(self, session_id: str) -> Optional[Session]:
    """
    Get a session by its ID.

    Returns:
      Optional[Session]: The session, if it exists.
    """
    return self._sessions.get(session_id)

  def delete_session(self, session_id: str):
    """
    Delete a session by its ID.
    """
    if session_id in self._sessions:
      del self._sessions[session_id]

  def encode_session(self, session_id: str) -> str:
    """
    Encode a session into a JWT.

    Returns:
      str: The JWT.
    """

    if self._secret is None:
      raise ValueError('JWT secret not set')

    session = self.get_session(session_id)
    if session is None:
      raise ValueError('Session not found')

    return jwt.encode(
      payload=session.model_dump(),
      key=self._secret,
      algorithm='HS256',
    )

  def decode_session(self, token: str) -> Optional[Session]:
    """
    Decode a JWT into a session.

    Returns:
      Optional[Session]: The session, if the token is valid.
    """
    if self._secret is None:
      raise ValueError('JWT secret not set')

    try:
      payload = jwt.decode(
        jwt=token,
        key=self._secret,
        algorithms=['HS256'],
      )
    except jwt.PyJWTError as e:
      self._logger.error(f'Error decoding JWT: {e}')
      return None

    return Session(**payload)
