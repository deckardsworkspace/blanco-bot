from utils.config import get_debug_guilds
from utils.database import Database
from utils.jockey_helpers import manual_await
from utils.lavalink_bot import LavalinkBot
from .debug import DebugCog
from .player import PlayerCog


def setup(bot: LavalinkBot):
    # Create Database instance
    db = Database(bot.config['bot']['database'])

    # Add cogs
    bot.add_cog(DebugCog(bot))
    bot.add_cog(PlayerCog(bot, db))

    # Sync slash commands
    manual_await(bot.sync_all_application_commands())
