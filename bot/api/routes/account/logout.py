from typing import TYPE_CHECKING

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse

from bot.api.depends.session import session_dependency

if TYPE_CHECKING:
  from bot.api.models.session import Session
  from bot.api.utils.session import SessionManager


async def logout(
  request: Request,
  session: 'Session' = Depends(session_dependency),
) -> RedirectResponse:
  session_manager: 'SessionManager' = request.app.state.session_manager
  session_manager.delete_session(session.session_id)

  return RedirectResponse(url='/')
