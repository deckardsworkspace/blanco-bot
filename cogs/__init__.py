from utils.lavalink_bot import LavalinkBot
from .debug import DebugCog
from .player import PlayerCog


def setup(bot: LavalinkBot):
    # Add cogs
    bot.add_cog(DebugCog(bot))
    bot.add_cog(PlayerCog(bot))

    # Sync slash commands
    bot.loop.create_task(bot.sync_all_application_commands())
