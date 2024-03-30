"""
Discord OAuth2 token view. Displayed on redirect from Discord auth flow.
"""

from time import time

import requests
from aiohttp import web
from aiohttp_session import get_session
from requests.exceptions import HTTPError, Timeout

from bot.dataclass.oauth import OAuth
from bot.utils.constants import DISCORD_API_BASE_URL, USER_AGENT


async def discordoauth(request: web.Request):  # noqa: PLR0911
  """
  Exchange the code for an access token and store it in the database.

  TODO: Refactor to have fewer returns.
  """
  # Get session
  session = await get_session(request)

  # Get state
  if 'state' not in session:
    return web.HTTPBadRequest(text='Missing state, try logging in again.')
  state = session['state']

  # Get OAuth ID, secret, and base URL
  oauth_id = request.app['config'].discord_oauth_id
  oauth_secret = request.app['config'].discord_oauth_secret
  base_url = request.app['config'].base_url

  # Get code
  try:
    code = request.query['code']
    state = request.query['state']
  except KeyError as err:
    return web.HTTPBadRequest(text=f'Missing parameter: {err.args[0]}')

  # Check state
  if state != session['state']:
    return web.HTTPBadRequest(text='Invalid state, try logging in again.')

  # Get access token
  response = requests.post(
    str(DISCORD_API_BASE_URL / 'oauth2/token'),
    data={
      'client_id': oauth_id,
      'client_secret': oauth_secret,
      'grant_type': 'authorization_code',
      'code': code,
      'redirect_uri': f'{base_url}/discordoauth',
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
    return web.HTTPBadRequest(text=f'Error getting access token: {err}')
  except Timeout:
    return web.HTTPBadRequest(text='Timed out while requesting access token')

  # Get user info
  parsed = response.json()
  user_info = requests.get(
    str(DISCORD_API_BASE_URL / 'users/@me'),
    headers={
      'Authorization': f'Bearer {parsed['access_token']}',
      'User-Agent': USER_AGENT,
    },
    timeout=5,
  )
  try:
    user_info.raise_for_status()
  except HTTPError as err:
    return web.HTTPBadRequest(text=f'Error getting user info: {err}')
  except Timeout:
    return web.HTTPBadRequest(text='Timed out while requesting user info')

  # Calculate expiry timestamp
  user_parsed = user_info.json()
  expires_at = int(time()) + parsed['expires_in']

  # Store user info in DB
  database = request.app['db']
  database.set_oauth(
    'discord',
    OAuth(
      user_id=user_parsed['id'],
      username=user_parsed['username'],
      access_token=parsed['access_token'],
      refresh_token=parsed['refresh_token'],
      expires_at=expires_at,
    ),
  )

  # Redirect to dashboard
  del session['state']
  session['user_id'] = user_parsed['id']
  return web.HTTPFound('/dashboard')
