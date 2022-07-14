from discord.ext.commands import Bot
from .player import PlayerCog


def setup(bot: Bot):
    bot.add_cog(PlayerCog(bot))
