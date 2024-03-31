"""
Main module for the web server.
"""

from base64 import urlsafe_b64decode
from typing import TYPE_CHECKING

import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from aiohttp_session import setup as setup_sessions
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography.fernet import Fernet

from bot.utils.logger import create_logger

from .routes import setup_routes

if TYPE_CHECKING:
  from bot.database import Database
from bot.models.config import Config


class AccessLogger(AbstractAccessLogger):
  """
  Custom access logger that logs the response status code, request method,
  path, and time taken to process the request.
  """

  def log(self, request, response, time):
    log_fmt = 'Server: %s %s %s (took %.2f ms)'
    self.logger.info(
      log_fmt, response.status, request.method, request.path, time * 1000
    )


async def run_app(database: 'Database', config: 'Config'):
  """
  Run the web server.
  """
  # Create logger
  logger = create_logger('server')

  # Create app
  app = web.Application()
  app['db'] = database
  app['config'] = config

  # Setup sessions
  fernet_key = Fernet.generate_key()
  setup_sessions(app, EncryptedCookieStorage(urlsafe_b64decode(fernet_key)))

  # Setup templates and routes
  aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('dashboard/templates'))
  setup_routes(app)

  # Run app
  runner = web.AppRunner(app, access_log=logger, access_log_class=AccessLogger)
  await runner.setup()
  site = web.TCPSite(runner, port=config.server_port)
  await site.start()

  logger.info('Web server listening on %s', config.base_url)
