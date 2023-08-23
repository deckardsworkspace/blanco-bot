from utils.blanco import BlancoBot
from .debug import DebugCog
from .player import PlayerCog


def setup(bot: BlancoBot):
    # Add cogs
    bot.add_cog(DebugCog(bot))
    bot.add_cog(PlayerCog(bot))
