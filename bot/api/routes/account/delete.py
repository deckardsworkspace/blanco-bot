from typing import TYPE_CHECKING

from fastapi import Depends
from fastapi.responses import RedirectResponse

from bot.api.depends.database import database_dependency
from bot.api.depends.session import session_dependency

if TYPE_CHECKING:
  from bot.api.models.session import Session
  from bot.database import Database


async def delete_account(
  db: 'Database' = Depends(database_dependency),
  session: 'Session' = Depends(session_dependency),
) -> RedirectResponse:
  user_id = session.user_id
  db.delete_oauth('lastfm', user_id)
  db.delete_oauth('spotify', user_id)
  db.delete_oauth('discord', user_id)

  return RedirectResponse(url='/account/logout')
