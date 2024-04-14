from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from starlette.status import HTTP_401_UNAUTHORIZED

if TYPE_CHECKING:
  from bot.api.models.session import Session
  from bot.api.utils.session import SessionManager

EXPECTED_AUTH_SCHEME = 'Bearer'
EXPECTED_AUTH_PARTS = 2


def session_dependency(request: Request) -> 'Session':
  """
  FastAPI dependency to get the requesting user's session object.

  Args:
    request (web.Request): The request.

  Returns:
    Session: The session object for the current Discord user.
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

  return session
