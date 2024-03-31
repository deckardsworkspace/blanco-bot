from secrets import token_urlsafe

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from yarl import URL

from bot.utils.config import config as bot_config


async def get_login_url() -> RedirectResponse:
  oauth_id = bot_config.discord_oauth_id
  base_url = bot_config.base_url

  if oauth_id is None or base_url is None:
    raise HTTPException(
      status_code=HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Missing Discord OAuth ID or base URL',
    )

  state = token_urlsafe(16)

  url = URL.build(
    scheme='https',
    host='discord.com',
    path='/api/oauth2/authorize',
    query={
      'client_id': oauth_id,
      'response_type': 'code',
      'scope': 'identify guilds email',
      'redirect_uri': f'{base_url}/oauth/discord',
      'state': state,
      'prompt': 'none',
    },
  )

  response = RedirectResponse(url=str(url))
  response.set_cookie('state', state, httponly=True, samesite='lax')
  return response
