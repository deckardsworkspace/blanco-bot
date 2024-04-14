from secrets import token_urlsafe
from typing import Tuple

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from yarl import URL

from bot.api.utils.constants import SPOTIFY_OAUTH_SCOPES
from bot.utils.config import config as bot_config


async def redirect_to_spotify_login() -> RedirectResponse:
  oauth_id = bot_config.spotify_client_id
  base_url = bot_config.base_url

  if oauth_id is None or base_url is None:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Missing Spotify OAuth ID or base URL',
    )

  state, url = _build_url(oauth_id, base_url)
  response = RedirectResponse(url=str(url))
  response.set_cookie('state', state, httponly=True, samesite='lax')
  return response


def _build_url(oauth_id: str, base_url: str) -> Tuple[str, str]:
  """
  Generate a state token and build the URL for the OAuth redirect.

  Args:
    oauth_id: The Spotify OAuth client ID.
    base_url: The base URL of the bot.

  Returns:
    Tuple[str, str]: The state token and URL.
  """

  state = token_urlsafe(16)

  url = URL.build(
    scheme='https',
    host='accounts.spotify.com',
    path='/authorize',
    query={
      'client_id': oauth_id,
      'response_type': 'code',
      'scope': ' '.join(SPOTIFY_OAUTH_SCOPES),
      'redirect_uri': f'{base_url}/callback/spotify',
      'state': state,
    },
  )

  return state, str(url)
