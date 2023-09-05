from utils.blanco import BlancoBot
from .main import run_app


def setup(bot: 'BlancoBot'):
    assert bot.config is not None
    bot.loop.create_task(run_app(bot.db, bot.config))
