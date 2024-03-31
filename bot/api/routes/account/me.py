"""
Route for getting the current user's account information.
"""

from typing import TYPE_CHECKING, Optional

from fastapi import Depends

from bot.api.depends.database import database_dependency
from bot.api.depends.session import session_dependency
from bot.api.models.account import AccountResponse

if TYPE_CHECKING:
  from bot.database import Database
  from bot.models.oauth import LastfmAuth, OAuth


async def get_logged_in_user(
  user: 'OAuth' = Depends(session_dependency),
  db: 'Database' = Depends(database_dependency),
) -> AccountResponse:
  spotify_username = None
  spotify: Optional['OAuth'] = db.get_oauth('spotify', user.user_id)
  if spotify is not None:
    spotify_username = spotify.username

  lastfm_username = None
  lastfm: Optional['LastfmAuth'] = db.get_lastfm_credentials(user.user_id)
  if lastfm is not None:
    lastfm_username = lastfm.username

  return AccountResponse(
    username=user.username,
    spotify_logged_in=spotify is not None,
    spotify_username=spotify_username,
    lastfm_logged_in=lastfm is not None,
    lastfm_username=lastfm_username,
  )
