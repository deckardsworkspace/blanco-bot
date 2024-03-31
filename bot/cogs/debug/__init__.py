"""
DebugCog: Cog for debugging commands.
"""

from typing import TYPE_CHECKING

from nextcord import Color, Interaction, PartialMessageable, SlashOption, slash_command
from nextcord.ext import application_checks
from nextcord.ext.commands import Cog

from bot.models.custom_embed import CustomEmbed
from bot.utils.embeds import create_success_embed
from bot.utils.logger import create_logger
from bot.utils.paginator import Paginator

if TYPE_CHECKING:
  from bot.utils.blanco import BlancoBot

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
  """
  Cog for debugging commands.
  """

  def __init__(self, bot: 'BlancoBot'):
    """
    Constructor for DebugCog.
    """
    self._bot = bot
    self._logger = create_logger(self.__class__.__name__)
    self._logger.info('Loaded DebugCog')

  @slash_command(name='announce')
  @application_checks.is_owner()
  async def announce(
    self,
    itx: Interaction,
    message: str = SlashOption(description='The message to announce.', required=True),
  ):
    """
    Posts an announcement to the system channel in all guilds.
    If there is no system channel, attempt to send to the last channel
    used by the bot for now playing embeds.
    """
    await itx.response.defer()

    # Create announcement embed
    embed = CustomEmbed(
      color=Color.yellow(),
      title=':warning: Announcement',
      description=message,
      footer='From the bot owner',
      timestamp_now=True,
    ).get()

    # Send announcement to all guilds
    for guild in self._bot.guilds:
      # Get system channel
      system_channel = guild.system_channel
      if system_channel is None:
        # Attempt to get status channel
        system_channel = self._bot.get_status_channel(guild.id)

      if system_channel is None or (
        not isinstance(system_channel, PartialMessageable)
        and not system_channel.permissions_for(guild.me).send_messages
      ):
        self._logger.error('No suitable announcement channel saved for %s', guild.name)
      else:
        # Send message
        await system_channel.send(embed=embed)
        self._logger.info('Sent announcement to %s', guild.name)

    await itx.followup.send(embed=create_success_embed('Announced!'), ephemeral=True)

  @slash_command(name='reload')
  @application_checks.is_owner()
  async def reload(self, itx: Interaction):
    """
    Reloads all bot.cogs.
    """
    # Reload cogs
    self._bot.unload_extension('cogs')
    self._bot.load_extension('cogs')

    # Resync commands
    await self._bot.sync_all_application_commands()

    await itx.response.send_message(
      embed=create_success_embed('Reloaded extensions!'), ephemeral=True
    )

  @slash_command(name='stats')
  async def stats(self, itx: Interaction):
    """
    Shows bot statistics.
    """
    await itx.response.defer()

    pages = []
    nodes = self._bot.pool.nodes
    for node in nodes:
      stats = node.stats

      if stats is not None:
        # Adapted from @ooliver1/mafic test bot
        pages.append(
          CustomEmbed(
            color=Color.purple(),
            title=f':bar_chart:｜Stats for node `{node.label}`',
            description='No statistics available'
            if stats is None
            else STATS_FORMAT.format(
              uptime=stats.uptime,
              used=stats.memory.used / 1024 / 1024,
              free=stats.memory.free / 1024 / 1024,
              allocated=stats.memory.allocated / 1024 / 1024,
              reservable=stats.memory.reservable / 1024 / 1024,
              system_load=stats.cpu.system_load * 100,
              lavalink_load=stats.cpu.lavalink_load * 100,
              player_count=stats.player_count,
              playing_player_count=stats.playing_player_count,
            ),
            footer=f'{len(nodes)} total node(s)',
          ).get()
        )
      else:
        pages.append(
          CustomEmbed(
            color=Color.red(),
            title=f':bar_chart:｜Stats for node `{node.label}`',
            description='No statistics available',
            footer=f'{len(nodes)} total node(s)',
          ).get()
        )

    # Run paginator
    paginator = Paginator(itx)
    return await paginator.run(pages)
