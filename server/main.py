from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from aiohttp_session import setup as setup_sessions
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from base64 import urlsafe_b64decode
from cryptography.fernet import Fernet
from typing import TYPE_CHECKING
from utils.logger import create_logger
from .routes import setup_routes
import aiohttp_jinja2
import jinja2
if TYPE_CHECKING:
    from database import Database
    from dataclass.config import Config


class AccessLogger(AbstractAccessLogger):
    def log(self, request, response, time):
        self.logger.info(f'Server: {response.status} {request.method}'
                         f' {request.path} (took {time*1000:.2f} ms)')


async def run_app(db: 'Database', config: 'Config'):
    # Create logger
    logger = create_logger('server', debug=config.debug_enabled)

    # Create app
    app = web.Application()
    app['db'] = db
    app['config'] = config

    # Setup sessions
    fernet_key = Fernet.generate_key()
    setup_sessions(app, EncryptedCookieStorage(urlsafe_b64decode(fernet_key)))

    # Setup templates and routes
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('server/templates'))
    setup_routes(app)

    # Run app
    runner = web.AppRunner(app, access_log=logger, access_log_class=AccessLogger)
    await runner.setup()
    site = web.TCPSite(runner, port=config.server_port)
    await site.start()

    logger.info(f'Web server started')
