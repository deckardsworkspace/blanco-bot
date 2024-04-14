from base64 import b64encode
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Tuple

from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from requests import HTTPError, Timeout, post
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from bot.api.depends.database import database_dependency
from bot.api.depends.user import user_dependency
from bot.models.oauth import OAuth
from bot.utils.config import config as bot_config
from bot.utils.constants import DISCORD_API_BASE_URL, USER_AGENT

if TYPE_CHECKING:
  from bot.database import Database


async def spotify_callback(  # noqa: PLR0913
  request: Request,
  response: Response,
  code: str,
  state: str,
  db: 'Database' = Depends(database_dependency),
  user: OAuth = Depends(user_dependency),
) -> RedirectResponse:
  _validate_state(request, response, state=state)

  oauth_id = bot_config.spotify_client_id
  oauth_secret = bot_config.spotify_client_secret
  base_url = bot_config.base_url
  if oauth_id is None or oauth_secret is None or base_url is None:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Missing Spotify OAuth ID, secret, or base URL',
    )

  access_token, refresh_token, expiration_time, scopes = _exchange_code_for_token(
    oauth_id, oauth_secret, base_url, code
  )
  _store_user_info(db, user, access_token, refresh_token, expiration_time, scopes)

  return RedirectResponse(url=base_url)


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
) -> Tuple[str, str, int, str]:
  """
  Exchange the code for an access token.

  Returns:
    Tuple[str, str, int, str]: The access token, refresh token,
      the token expiration timestamp, and the list of authorized
      scopes.
  """

  response = post(
    str(DISCORD_API_BASE_URL / 'token'),
    data={
      'grant_type': 'authorization_code',
      'code': code,
      'redirect_uri': f'{base_url}/callback/spotify',
    },
    headers={
      'Authorization': f'Basic {b64encode(f"{client_id}:{client_secret}".encode()).decode()}',
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
  scopes = data['scope']
  expiration_time = int(datetime.now(UTC).timestamp()) + expires_in

  return access_token, refresh_token, expiration_time, scopes


def _store_user_info(  # noqa: PLR0913
  db: 'Database',
  user: OAuth,
  access_token: str,
  refresh_token: str,
  expiration_time: int,
  scopes: str,
):
  db.set_oauth(
    'spotify',
    OAuth(
      user_id=user.user_id,
      username=user.username,
      access_token=access_token,
      refresh_token=refresh_token,
      expires_at=expiration_time,
    ),
  )

  db.set_spotify_scopes(
    user.user_id,
    scopes.split(' '),
  )
