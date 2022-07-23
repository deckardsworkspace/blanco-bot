from utils.database import Database
from utils.jockey_helpers import manual_await
from utils.lavalink_bot import LavalinkBot
from .player import PlayerCog


def setup(bot: LavalinkBot):
    # Create Database instance
    db = Database(bot.config['database'])

    # Add cogs
    bot.add_cog(PlayerCog(bot, db))

    # Sync slash commands
    manual_await(bot.sync_application_commands())
