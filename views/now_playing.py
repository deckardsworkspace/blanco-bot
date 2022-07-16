from lavalink.models import DefaultPlayer
from nextcord import ButtonStyle, Interaction
from nextcord.ui import button, Button, View
from utils.lavalink_bot import LavalinkBot


class NowPlayingView(View):
    def __init__(self, bot: LavalinkBot, player: DefaultPlayer):
        super().__init__(timeout=None)
        self._cog = bot.get_cog('PlayerCog')
        self._player = player
    
    @button(label='Prev', style=ButtonStyle.grey)
    async def skip_backward(self, _: Button, interaction: Interaction):
        return await self._cog.previous(interaction)

    @button(label='Play/Pause', style=ButtonStyle.blurple)
    async def toggle_pause(self, _: Button, interaction: Interaction):
        if self._player.paused:
            return await self._cog.unpause(interaction)
        return await self._cog.pause(interaction)

    @button(label='Next', style=ButtonStyle.grey)
    async def skip_forward(self, _: Button, interaction: Interaction):
        return await self._cog.skip(interaction)
    
    @button(label='Stop', style=ButtonStyle.red)
    async def stop(self, _: Button, interaction: Interaction):
        return await self._cog.stop(interaction)
