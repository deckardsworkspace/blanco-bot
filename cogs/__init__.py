from discord.ext.commands import Bot
from os import environ
from utils.database import Database
from utils.jockey_helpers import manual_await
from .player import PlayerCog


def setup(bot: Bot):
    # Create Database instance
    db = Database(environ['DB_FILENAME'])

    # Add cogs
    bot.add_cog(PlayerCog(bot, db))

    # Sync slash commands
    manual_await(bot.sync_application_commands())
