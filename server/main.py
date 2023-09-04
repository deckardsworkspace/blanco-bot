from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from typing import TYPE_CHECKING
from utils.logger import create_logger
from .routes import setup_routes
import aiohttp_jinja2
import jinja2
if TYPE_CHECKING:
    from database import Database


class AccessLogger(AbstractAccessLogger):
    def log(self, request, response, time):
        self.logger.info(f'Server: {response.status} {request.method}'
                         f' {request.path} (took {time*1000:.2f} ms)')


async def run_app(db: 'Database', debug: bool):
    # Create logger
    logger = create_logger('server', debug=debug)

    # Create app
    app = web.Application()
    app['db'] = db
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('server/templates'))
    setup_routes(app)
    runner = web.AppRunner(app, access_log=logger, access_log_class=AccessLogger)
    await runner.setup()
    site = web.TCPSite(runner)
    await site.start()

    logger.info(f'Web server started')
