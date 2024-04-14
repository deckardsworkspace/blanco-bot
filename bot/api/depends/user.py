from typing import TYPE_CHECKING, Optional

from fastapi import Depends, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

from .database import database_dependency
from .session import session_dependency

if TYPE_CHECKING:
  from bot.api.models.session import Session
  from bot.database import Database
  from bot.models.oauth import OAuth


def user_dependency(
  db: 'Database' = Depends(database_dependency),
  session: 'Session' = Depends(session_dependency),
) -> 'OAuth':
  """
  FastAPI dependency to get the requesting user's info.

  Returns:
    OAuth: The info for the current Discord user.
  """

  user: Optional['OAuth'] = db.get_oauth('discord', session.user_id)
  if user is None:
    raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail='User not found')

  return user
