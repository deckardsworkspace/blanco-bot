from typing import TYPE_CHECKING, Optional

from fastapi import Depends, HTTPException, Request
from starlette.status import HTTP_401_UNAUTHORIZED

from .database import database_dependency

if TYPE_CHECKING:
  from bot.api.utils.session import SessionManager
  from bot.database import Database
  from bot.models.oauth import OAuth


EXPECTED_AUTH_SCHEME = 'Bearer'
EXPECTED_AUTH_PARTS = 2


def session_dependency(
  request: Request, db: 'Database' = Depends(database_dependency)
) -> 'OAuth':
  """
  FastAPI dependency to get the requesting user's info.

  Args:
    request (web.Request): The request.

  Returns:
    OAuth: The info for the current Discord user.
  """

  authorization = request.headers.get('Authorization')
  if authorization is None:
    raise HTTPException(
      status_code=HTTP_401_UNAUTHORIZED, detail='No authorization header'
    )

  parts = authorization.split()
  if len(parts) != EXPECTED_AUTH_PARTS:
    raise HTTPException(
      status_code=HTTP_401_UNAUTHORIZED, detail='Invalid authorization header'
    )

  scheme, token = parts
  if scheme != EXPECTED_AUTH_SCHEME:
    raise HTTPException(
      status_code=HTTP_401_UNAUTHORIZED, detail='Invalid authorization scheme'
    )

  session_manager: 'SessionManager' = request.app.state.session_manager
  session = session_manager.decode_session(token)
  if session is None:
    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail='Invalid session')

  user: Optional['OAuth'] = db.get_oauth('discord', session.user_id)
  if user is None:
    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail='User not found')

  return user
