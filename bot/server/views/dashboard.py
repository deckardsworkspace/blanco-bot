"""
Dashboard view.
"""

from typing import TYPE_CHECKING

import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session

if TYPE_CHECKING:
  from bot.models.oauth import LastfmAuth, OAuth


@aiohttp_jinja2.template('dashboard.html')
async def dashboard(request: web.Request):
  """
  Render the dashboard.
  """
  # Get session
  session = await get_session(request)
  if 'user_id' not in session:
    return web.HTTPFound('/login')

  # Get user info
  database = request.app['db']
  user: OAuth = database.get_oauth('discord', session['user_id'])
  if user is None:
    return web.HTTPFound('/login')

  # Get Spotify info
  spotify_username = None
  spotify: OAuth = database.get_oauth('spotify', session['user_id'])
  if spotify is not None:
    spotify_username = spotify.username

  # Get Last.fm info
  lastfm_username = None
  lastfm: LastfmAuth = database.get_lastfm_credentials(session['user_id'])
  if lastfm is not None:
    lastfm_username = lastfm.username

  # Render template
  return {
    'username': user.username,
    'spotify_logged_in': spotify is not None,
    'spotify_username': spotify_username,
    'lastfm_logged_in': lastfm is not None,
    'lastfm_username': lastfm_username,
  }
