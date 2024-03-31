from datetime import UTC, datetime
from typing import TYPE_CHECKING, Tuple

from fastapi import Depends, HTTPException, Request, Response
from requests import HTTPError, Timeout, get, post
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from bot.api.depends.database import database_dependency
from bot.api.models.oauth import DiscordUser, OAuthResponse
from bot.models.oauth import OAuth
from bot.utils.config import config as bot_config
from bot.utils.constants import DISCORD_API_BASE_URL, USER_AGENT

if TYPE_CHECKING:
  from bot.api.utils.session import SessionManager
  from bot.database import Database


async def discord_oauth(
  request: Request,
  response: Response,
  code: str,
  state: str,
  db: 'Database' = Depends(database_dependency),
) -> OAuthResponse:
  _validate_state(request, response, state=state)

  oauth_id = bot_config.discord_oauth_id
  oauth_secret = bot_config.discord_oauth_secret
  base_url = bot_config.base_url
  if oauth_id is None or oauth_secret is None or base_url is None:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Missing Discord OAuth ID, secret, or base URL',
    )

  access_token, refresh_token, expiration_time = _exchange_code_for_token(
    oauth_id, oauth_secret, base_url, code
  )
  user = _get_user_info(access_token)
  _store_user_info(db, user, access_token, refresh_token, expiration_time)

  session_manager: 'SessionManager' = request.app.state.session_manager
  session_id = session_manager.create_session(user.id)
  jwt = session_manager.encode_session(session_id)

  return OAuthResponse(session_id=session_id, jwt=jwt)


def _validate_state(request: Request, response: Response, state: str) -> str:
  expected_state = request.cookies.get('state')
  if expected_state is None:
    raise HTTPException(
      status_code=HTTP_400_BAD_REQUEST,
      detail='Missing state cookie',
    )

  if state != expected_state:
    raise HTTPException(
      status_code=HTTP_400_BAD_REQUEST,
      detail='Invalid state',
    )

  response.delete_cookie('state')
  return state


def _exchange_code_for_token(
  client_id: str, client_secret: str, base_url: str, code: str
) -> Tuple[str, str, int]:
  """
  Exchange the code for an access token.

  Returns:
    Tuple[str, str, int]: The access token, refresh token,
      and the time at which the access token expires.
  """

  response = post(
    str(DISCORD_API_BASE_URL / 'oauth2/token'),
    data={
      'client_id': client_id,
      'client_secret': client_secret,
      'grant_type': 'authorization_code',
      'code': code,
      'redirect_uri': f'{base_url}/oauth/discord',
    },
    headers={
      'Content-Type': 'application/x-www-form-urlencoded',
      'User-Agent': USER_AGENT,
    },
    timeout=5,
  )

  try:
    response.raise_for_status()
  except HTTPError as err:
    raise HTTPException(
      status_code=HTTP_400_BAD_REQUEST, detail=f'Error getting access token: {err}'
    )
  except Timeout:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Timed out while requesting access token',
    )

  data = response.json()
  access_token = data['access_token']
  refresh_token = data['refresh_token']
  expires_in = data['expires_in']
  expiration_time = int(datetime.now(UTC).timestamp()) + expires_in

  return access_token, refresh_token, expiration_time


def _get_user_info(access_token: str) -> DiscordUser:
  response = get(
    str(DISCORD_API_BASE_URL / 'users/@me'),
    headers={
      'Authorization': f'Bearer {access_token}',
      'User-Agent': USER_AGENT,
    },
    timeout=5,
  )

  try:
    response.raise_for_status()
  except HTTPError as err:
    raise HTTPException(
      status_code=HTTP_400_BAD_REQUEST, detail=f'Error getting user info: {err}'
    )
  except Timeout:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Timed out while requesting user info',
    )

  data = response.json()
  return DiscordUser(
    id=data['id'],
    username=data['username'],
    discriminator=data['discriminator'],
    avatar=data.get('avatar'),
  )


def _store_user_info(
  db: 'Database',
  user: DiscordUser,
  access_token: str,
  refresh_token: str,
  expiration_time: int,
):
  db.set_oauth(
    'discord',
    OAuth(
      user_id=user.id,
      username=user.username,
      access_token=access_token,
      refresh_token=refresh_token,
      expires_at=expiration_time,
    ),
  )
