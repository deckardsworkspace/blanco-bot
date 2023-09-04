from typing import TYPE_CHECKING
from .debug import DebugCog
from .player import PlayerCog
if TYPE_CHECKING:
    from utils.blanco import BlancoBot


def setup(bot: 'BlancoBot'):
    # Add cogs
    bot.add_cog(DebugCog(bot))
    bot.add_cog(PlayerCog(bot))
