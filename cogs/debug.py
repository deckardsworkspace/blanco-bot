from dataclass.custom_embed import CustomEmbed
from nextcord import Color, Interaction, slash_command
from nextcord.ext import application_checks
from nextcord.ext.commands import Cog
from utils.jockey_helpers import create_success_embed
from utils.lavalink_bot import LavalinkBot
from utils.paginator import Paginator


STATS_FORMAT = """
```asciidoc
Uptime  :: {uptime}
Players :: {playing_player_count} playing ({player_count} total)
CPU     :: {system_load:.2f}% (Lavalink {lavalink_load:.2f}%)
Memory  :: {used:.0f} MiB used
           {free:.0f} MiB free
           {allocated:.0f} MiB allocated
           {reservable:.0f} MiB reservable
```
"""

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
    
    @slash_command(name='stats')
    @application_checks.is_owner()
    async def stats(self, itx: Interaction):
        """
        Shows bot statistics.
        """
        await itx.response.defer()

        pages = []
        nodes = self._bot.pool.nodes
        for node in nodes:
            stats = node.stats
            
            # Adapted from @ooliver1/mafic test bot
            pages.append(CustomEmbed(
                color=Color.purple(),
                title=f':bar_chart:｜Stats for node `{node.label}`',
                description='No statistics available' if stats is None else STATS_FORMAT.format(
                    uptime=stats.uptime,
                    used=stats.memory.used / 1024 / 1024,
                    free=stats.memory.free / 1024 / 1024,
                    allocated=stats.memory.allocated / 1024 / 1024,
                    reservable=stats.memory.reservable / 1024 / 1024,
                    system_load=stats.cpu.system_load * 100,
                    lavalink_load=stats.cpu.lavalink_load * 100,
                    player_count=stats.player_count,
                    playing_player_count=stats.playing_player_count
                ),
                footer=f'{len(nodes)} total node(s)'
            ).get())

        # Run paginator
        paginator = Paginator(itx)
        return await paginator.run(pages)
