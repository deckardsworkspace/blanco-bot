"""
Nextcord extension that runs the server for the bot.
"""

from utils.blanco import BlancoBot

from .main import run_app


def setup(bot: 'BlancoBot'):
  """
  Run the web server as an async task.
  """
  assert bot.config is not None
  bot.loop.create_task(run_app(bot.database, bot.config))
