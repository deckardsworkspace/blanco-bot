from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
  from bot.database import Database


def database_dependency(request: Request) -> 'Database':
  """
  FastAPI dependency to get the database object.

  Args:
    request (web.Request): The request.

  Returns:
    Database: The database object.
  """

  state = request.app.state
  if not hasattr(state, 'database'):
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail='No database connection'
    )

  database: 'Database' = state.database
  if database is None:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail='No database connection'
    )

  return database
