from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from typing import TYPE_CHECKING
from utils.logger import create_logger
from .routes import setup_routes
if TYPE_CHECKING:
    from database import Database
    from utils.blanco import BlancoBot


class AccessLogger(AbstractAccessLogger):
    def log(self, request, response, time):
        self.logger.info(f'Server: {response.status} {request.method}'
                         f' {request.path} (took {time*1000:.2f} ms)')


async def run_app(db: 'Database', debug: bool):
    # Create logger
    logger = create_logger('server', debug=debug)

    # Create app
    app = web.Application()
    setup_routes(app)
    app['db'] = db
    runner = web.AppRunner(app, access_log=logger, access_log_class=AccessLogger)
    await runner.setup()
    site = web.TCPSite(runner)
    await site.start()

    logger.info(f'Web server started')


def setup(bot: 'BlancoBot'):
    assert bot.config is not None
    bot.loop.create_task(run_app(bot.db, bot.config.debug_enabled))
