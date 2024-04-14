from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException
from fastapi.responses import Response
from starlette.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST

from bot.api.depends.database import database_dependency
from bot.api.depends.user import user_dependency
from bot.api.models.account import UnlinkRequest

if TYPE_CHECKING:
  from bot.database import Database
  from bot.models.oauth import OAuth

VALID_SERVICES = ('lastfm', 'spotify')


async def unlink_service(
  request: UnlinkRequest,
  db: 'Database' = Depends(database_dependency),
  user: 'OAuth' = Depends(user_dependency),
) -> Response:
  service = request.service
  if service not in VALID_SERVICES:
    raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='Invalid service')

  db.delete_oauth(service, user.user_id)

  return Response(status_code=HTTP_204_NO_CONTENT)
