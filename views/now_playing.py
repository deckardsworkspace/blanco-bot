from nextcord import ButtonStyle, Interaction
from nextcord.ui import button, View
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from cogs.player import PlayerCog
    from nextcord import Interaction
    from nextcord.ui import Button
    from utils.jockey import Jockey
    from utils.blanco import BlancoBot


class NowPlayingView(View):
    def __init__(self, bot: 'BlancoBot', player: 'Jockey', spotify_id: Optional[str] = None):
        super().__init__(timeout=None)
        self._bot = bot
        self._cog: 'PlayerCog' = bot.get_cog('PlayerCog') # type: ignore
        if self._cog is None:
            raise ValueError('PlayerCog not found')
        
        self._spotify_id = spotify_id
        self._player = player
    
    @button(label='📋', style=ButtonStyle.green)
    async def queue(self, _: 'Button', interaction: 'Interaction'):
        return await self._cog.queue(interaction)
    
    @button(label='⏮️', style=ButtonStyle.grey)
    async def skip_backward(self, _: 'Button', interaction: 'Interaction'):
        return await self._cog.previous(interaction)

    @button(label='⏯️', style=ButtonStyle.blurple)
    async def toggle_pause(self, _: 'Button', interaction: 'Interaction'):
        if self._player.paused:
            return await self._cog.unpause(interaction)
        return await self._cog.pause(interaction)

    @button(label='⏭️', style=ButtonStyle.grey)
    async def skip_forward(self, _: 'Button', interaction: 'Interaction'):
        return await self._cog.skip(interaction)
    
    @button(label='⏹️', style=ButtonStyle.red)
    async def stop(self, _: 'Button', interaction: 'Interaction'):
        return await self._cog.stop(interaction)
    
    @button(label='Like on Spotify', style=ButtonStyle.grey)
    async def like(self, _: 'Button', interaction: 'Interaction'):
        if not interaction.user:
            return
        
        await interaction.response.defer(ephemeral=True)
        if self._spotify_id is None:
            return await interaction.followup.send('This track does not have a Spotify ID.')
        
        # Get Spotify client
        try:
            spotify = self._bot.get_spotify_client(interaction.user.id)
        except ValueError as e:
            return await interaction.followup.send(e.args[0])
        
        # Save track
        try:
            spotify.save_track(self._spotify_id)
        except Exception as e:
            return await interaction.followup.send(f'Error liking track: {e}')
        
        # Send response
        return await interaction.followup.send('Added to your Liked Songs.')
    
    @button(label='Toggle shuffle', style=ButtonStyle.grey)
    async def shuffle(self, _: 'Button', interaction: 'Interaction'):
        status = self._player.is_shuffling
        if status:
            return await self._cog.unshuffle(interaction)
        return await self._cog.shuffle(interaction)
