from dataclass.custom_embed import CustomEmbed
from nextcord import Colour, SelectOption
from nextcord.ui import Select, View
from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from cogs.player import PlayerCog
    from nextcord import Interaction
    from utils.blanco import BlancoBot


class SpotifyDropdown(Select):
    def __init__(self, bot: 'BlancoBot', playlists: Dict[str, str], user_id: int):
        self._cog: 'PlayerCog' = bot.get_cog('PlayerCog') # type: ignore
        self._user_id = user_id
        self._choices = playlists
        
        options = [
            SelectOption(label=playlist_name, value=playlist_id)
            for playlist_id, playlist_name in playlists.items()
        ]
        super().__init__(
            placeholder='Select a playlist...',
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: 'Interaction'):
        # Ignore if the user isn't the one who invoked the command
        if not interaction.user or interaction.user.id != self._user_id:
            return
        
        # Edit message
        playlist_id = self.values[0]
        playlist_url = f'https://open.spotify.com/playlist/{playlist_id}'
        if interaction.message:
            embed = CustomEmbed(
                color=Colour.yellow(),
                title=':hourglass:｜Loading...',
                description=f'Selected playlist [{self._choices[playlist_id]}]({playlist_url}).'
            )
            await interaction.message.edit(
                embed=embed.get(),
                view=None
            )
        
        # Call the `/play` command with the playlist URL
        await self._cog.play(interaction, query=playlist_url)

        # Delete message
        if interaction.message:
            await interaction.message.delete()


class SpotifyDropdownView(View):
    def __init__(self, bot: 'BlancoBot', playlists: Dict[str, str], user_id: int):
        super().__init__(timeout=None)

        self.add_item(SpotifyDropdown(bot, playlists, user_id))
