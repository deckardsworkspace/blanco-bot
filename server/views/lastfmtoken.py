"""
Last.fm token view. Displayed on redirect from Last.fm auth flow.
"""

from hashlib import md5

import requests
from aiohttp import web
from aiohttp_session import get_session
from requests.exceptions import HTTPError, Timeout

from dataclass.oauth import LastfmAuth
from utils.constants import LASTFM_API_BASE_URL, USER_AGENT


async def lastfm_token(request: web.Request):
  """
  Exchange the token for a session key and store it in the database.
  """
  # Get session
  session = await get_session(request)

  # Get state and Discord user ID
  if 'user_id' not in session:
    return web.HTTPBadRequest(text='You are not logged into Blanco with Discord.')
  user_id = session['user_id']

  # Get API key and secret
  api_key = request.app['config'].lastfm_api_key
  secret = request.app['config'].lastfm_shared_secret

  # Get token
  try:
    token = request.query['token']
  except KeyError:
    return web.HTTPBadRequest(text='Missing token, try logging in again.')

  # Create signature
  signature = ''.join(
    ['api_key', api_key, 'method', 'auth.getSession', 'token', token, secret]
  )
  hashed = md5(signature.encode('utf-8')).hexdigest()

  # Get session key
  url = LASTFM_API_BASE_URL.with_query(
    {
      'method': 'auth.getSession',
      'api_key': api_key,
      'token': token,
      'api_sig': hashed,
      'format': 'json',
    }
  )

  # Get response
  response = requests.get(str(url), headers={'User-Agent': USER_AGENT}, timeout=5)
  try:
    response.raise_for_status()
  except HTTPError as err:
    return web.HTTPBadRequest(text=f'Error logging into Last.fm: {err}')
  except Timeout:
    return web.HTTPBadRequest(text='Timed out while requesting session key')

  # Get JSON
  json = response.json()
  try:
    session_key = json['session']['key']
    username = json['session']['name']
  except KeyError as err:
    return web.HTTPBadRequest(text=f'Error logging into Last.fm: missing {err.args[0]}')

  # Store user info in DB
  database = request.app['db']
  database.set_lastfm_credentials(
    LastfmAuth(user_id=user_id, username=username, session_key=session_key)
  )

  # Redirect to dashboard
  return web.HTTPFound('/dashboard')
