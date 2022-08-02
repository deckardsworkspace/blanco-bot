from nextcord import Interaction, slash_command
from nextcord.ext import application_checks
from nextcord.ext.commands import Cog
from utils.jockey_helpers import create_success_embed
from utils.lavalink_bot import LavalinkBot

class DebugCog(Cog):
    def __init__(self, bot: LavalinkBot):
        self._bot = bot
        print(f'Loaded cog: {self.__class__.__name__}')
    
    @slash_command(name='reload')
    @application_checks.is_owner()
    async def reload(self, itx: Interaction):
        """
        Reloads all cogs.
        """
        self._bot.unload_extension('cogs')
        self._bot.load_extension('cogs')
        await itx.response.send_message(embed=create_success_embed('Reloaded extensions!'), ephemeral=True)
