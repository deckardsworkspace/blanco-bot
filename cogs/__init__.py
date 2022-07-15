from discord.ext.commands import Bot
from os import environ
from utils.database import Database
from .player import PlayerCog


def setup(bot: Bot):
    # Create Database instance
    db = Database(environ['DB_FILENAME'])

    # Add cogs
    bot.add_cog(PlayerCog(bot, db))
