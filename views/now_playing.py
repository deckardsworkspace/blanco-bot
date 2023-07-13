from nextcord import ButtonStyle, Interaction
from nextcord.ui import button, Button, View
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cogs.player import PlayerCog
    from utils.jockey import Jockey
    from utils.lavalink_bot import LavalinkBot


class NowPlayingView(View):
    def __init__(self, bot: 'LavalinkBot', player: 'Jockey'):
        super().__init__(timeout=None)
        self._cog: 'PlayerCog' = bot.get_cog('PlayerCog') # type: ignore
        if self._cog is None:
            raise ValueError('PlayerCog not found')
        self._player = player
    
    @button(label=' 📋 ', style=ButtonStyle.green)
    async def queue(self, _: Button, interaction: Interaction):
        return await self._cog.queue(interaction)
    
    @button(label=' ⏮️ ', style=ButtonStyle.grey)
    async def skip_backward(self, _: Button, interaction: Interaction):
        return await self._cog.previous(interaction)

    @button(label=' ⏯️ ', style=ButtonStyle.blurple)
    async def toggle_pause(self, _: Button, interaction: Interaction):
        if self._player.paused:
            return await self._cog.unpause(interaction)
        return await self._cog.pause(interaction)

    @button(label=' ⏭️ ', style=ButtonStyle.grey)
    async def skip_forward(self, _: Button, interaction: Interaction):
        return await self._cog.skip(interaction)
    
    @button(label=' ⏹️ ', style=ButtonStyle.red)
    async def stop(self, _: Button, interaction: Interaction):
        return await self._cog.stop(interaction)
