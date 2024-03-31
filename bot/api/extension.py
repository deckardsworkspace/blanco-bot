"""
Nextcord extension that runs the API server for the bot
"""

from typing import TYPE_CHECKING

from .main import run_app

if TYPE_CHECKING:
  from bot.utils.blanco import BlancoBot


def setup(bot: 'BlancoBot'):
  """
  Run the API server within the bot's existing event loop.
  """
  run_app(bot.loop, bot.database)
