from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from yarl import URL

from bot.utils.config import config as bot_config


async def redirect_to_lastfm_login() -> RedirectResponse:
  api_key = bot_config.lastfm_api_key
  base_url = bot_config.base_url

  if api_key is None or base_url is None:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Missing Last.fm API key or base URL',
    )

  url = _build_url(api_key, base_url)
  response = RedirectResponse(url=str(url))
  return response


def _build_url(api_key: str, base_url: str) -> str:
  """
  Generate a state token and build the URL for the login redirect.

  Args:
    api_key: The Last.fm API key
    base_url: The base URL of the bot.

  Returns:
    str: The URL.
  """

  url = URL.build(
    scheme='https',
    host='www.last.fm',
    path='/api/auth',
    query={
      'api_key': api_key,
      'cb': f'{base_url}/callback/lastfm',
    },
  )

  return str(url)
