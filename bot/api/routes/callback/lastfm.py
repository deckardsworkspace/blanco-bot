from hashlib import md5
from typing import TYPE_CHECKING, Tuple

from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse
from requests import HTTPError, Timeout, request
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from bot.api.depends.database import database_dependency
from bot.api.depends.user import user_dependency
from bot.models.oauth import LastfmAuth, OAuth
from bot.utils.config import config as bot_config
from bot.utils.constants import LASTFM_API_BASE_URL, USER_AGENT

if TYPE_CHECKING:
  from bot.database import Database


async def lastfm_callback(
  token: str,
  db: 'Database' = Depends(database_dependency),
  user: OAuth = Depends(user_dependency),
) -> RedirectResponse:
  api_key = bot_config.lastfm_api_key
  secret = bot_config.lastfm_shared_secret

  if api_key is None or secret is None:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Missing Last.fm API key or shared secret',
    )

  session_key_url = _create_session_key_url(api_key, token, secret)
  session_key, username = _get_session_key(session_key_url)
  _store_user_info(db, user, session_key, username)

  return RedirectResponse(url='/')


def _create_session_key_url(api_key: str, token: str, secret: str) -> str:
  signature = ''.join(
    ['api_key', api_key, 'method', 'auth.getSession', 'token', token, secret]
  )

  hashed = md5(signature.encode('utf-8')).hexdigest()

  url = LASTFM_API_BASE_URL.with_query(
    {
      'method': 'auth.getSession',
      'api_key': api_key,
      'token': token,
      'api_sig': hashed,
      'format': 'json',
    }
  )

  return str(url)


def _get_session_key(url: str) -> Tuple[str, str]:
  response = request(
    'GET',
    url,
    headers={
      'User-Agent': USER_AGENT,
    },
    timeout=5,
  )

  try:
    response.raise_for_status()
  except HTTPError as err:
    raise HTTPException(
      status_code=HTTP_400_BAD_REQUEST,
      detail=f'Error getting session key: {err}',
    )
  except Timeout:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Timed out while requesting access token',
    )

  data = response.json()
  session_key = data['session']['key']
  username = data['session']['name']

  return session_key, username


def _store_user_info(db: 'Database', user: OAuth, session_key: str, username: str):
  db.set_lastfm_credentials(
    LastfmAuth(
      user_id=user.user_id,
      username=username,
      session_key=session_key,
    ),
  )
