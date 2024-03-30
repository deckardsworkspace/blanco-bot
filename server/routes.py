"""
Adds routes to the application.
"""

from typing import TYPE_CHECKING

from .views.dashboard import dashboard
from .views.deleteaccount import delete_account
from .views.discordoauth import discordoauth
from .views.homepage import homepage
from .views.lastfmtoken import lastfm_token
from .views.linklastfm import link_lastfm
from .views.linkspotify import link_spotify
from .views.login import login
from .views.logout import logout
from .views.robotstxt import robotstxt
from .views.spotifyoauth import spotifyoauth
from .views.unlink import unlink

if TYPE_CHECKING:
  from aiohttp.web import Application


def setup_routes(app: 'Application'):
  """
  Add all available routes to the application.
  """
  app.router.add_get('/', homepage)
  app.router.add_get('/dashboard', dashboard)
  app.router.add_get('/deleteaccount', delete_account)
  app.router.add_get('/discordoauth', discordoauth)
  app.router.add_get('/lastfmtoken', lastfm_token)
  app.router.add_get('/linklastfm', link_lastfm)
  app.router.add_get('/linkspotify', link_spotify)
  app.router.add_get('/login', login)
  app.router.add_get('/logout', logout)
  app.router.add_get('/robots.txt', robotstxt)
  app.router.add_get('/spotifyoauth', spotifyoauth)
  app.router.add_get('/unlink', unlink)
  app.router.add_static('/static/', path='server/static', name='static')
