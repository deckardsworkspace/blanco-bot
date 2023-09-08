"""
Now Playing view for the player.
"""

from typing import TYPE_CHECKING, Optional

from nextcord import ButtonStyle
from nextcord.ui import View, button
from requests.exceptions import HTTPError, Timeout

from utils.exceptions import VoiceCommandError
from utils.jockey_helpers import create_error_embed, create_success_embed
from utils.player_checks import check_mutual_voice

if TYPE_CHECKING:
    from nextcord import Interaction
    from nextcord.ui import Button

    from cogs.player import PlayerCog
    from utils.blanco import BlancoBot
    from utils.jockey import Jockey


class NowPlayingView(View):
    """
    View for the Now Playing message, which contains buttons for interacting
    with the player.
    """
    def __init__(self, bot: 'BlancoBot', player: 'Jockey', spotify_id: Optional[str] = None):
        super().__init__(timeout=None)
        self._bot = bot
        self._cog: 'PlayerCog' = bot.get_cog('PlayerCog') # type: ignore
        if self._cog is None:
            raise ValueError('PlayerCog not found')

        self._spotify_id = spotify_id
        self._player = player

    async def _check_mutual_voice(self, interaction: 'Interaction') -> bool:
        """
        Check if the user is in the same voice channel as the bot.
        """
        try:
            _ = check_mutual_voice(interaction)
        except VoiceCommandError as err:
            await interaction.response.send_message(err.args[0], ephemeral=True)
            return False

        return True

    @button(label='📋', style=ButtonStyle.green)
    async def queue(self, _: 'Button', interaction: 'Interaction'):
        """
        Display the current queue.
        """
        if await self._check_mutual_voice(interaction):
            return await self._cog.queue(interaction)

    @button(label='⏮️', style=ButtonStyle.grey)
    async def skip_backward(self, _: 'Button', interaction: 'Interaction'):
        """
        Skip to the previous track.
        """
        if await self._check_mutual_voice(interaction):
            return await self._cog.previous(interaction)

    @button(label='⏸️', style=ButtonStyle.blurple)
    async def toggle_pause(self, btn: 'Button', interaction: 'Interaction'):
        """
        Toggle pause on the current track.
        """
        if await self._check_mutual_voice(interaction):
            if self._player.paused:
                btn.label = '⏸️'
                await interaction.response.edit_message(view=self)
                return await self._cog.unpause(interaction, quiet=True)
            
            btn.label = '▶️'
            await interaction.response.edit_message(view=self)
            return await self._cog.pause(interaction, quiet=True)

    @button(label='⏭️', style=ButtonStyle.grey)
    async def skip_forward(self, _: 'Button', interaction: 'Interaction'):
        """
        Skip to the next track.
        """
        if await self._check_mutual_voice(interaction):
            return await self._cog.skip(interaction)

    @button(label='⏹️', style=ButtonStyle.red)
    async def stop_player(self, _: 'Button', interaction: 'Interaction'):
        """
        Stop the player.
        """
        if await self._check_mutual_voice(interaction):
            return await self._cog.stop(interaction)

    @button(label='Like on Spotify', style=ButtonStyle.grey)
    async def like(self, _: 'Button', interaction: 'Interaction'):
        """
        Like the current track on Spotify.
        """
        if not interaction.user:
            return

        await interaction.response.defer(ephemeral=True)
        if self._spotify_id is None:
            return await interaction.followup.send(
                embed=create_error_embed('This track does not have a Spotify ID.'),
                ephemeral=True
            )

        # Get Spotify client
        try:
            spotify = self._bot.get_spotify_client(interaction.user.id)
            if spotify is None:
                raise ValueError('Spotify client not initialized')
        except ValueError as err:
            return await interaction.followup.send(err.args[0])

        # Save track
        try:
            spotify.save_track(self._spotify_id)
        except (HTTPError, Timeout) as err:
            return await interaction.followup.send(
                embed=create_error_embed(f'Could not Like track: {err}'),
                ephemeral=True
            )

        # Send response
        return await interaction.followup.send(
            embed=create_success_embed('Added to your Liked Songs.'),
            ephemeral=True
        )

    @button(label='Shuffle', style=ButtonStyle.grey)
    async def shuffle(self, btn: 'Button', interaction: 'Interaction'):
        """
        Toggle shuffle on the current queue.
        """
        if await self._check_mutual_voice(interaction):
            status = self._player.is_shuffling
            if status:
                btn.label = 'Shuffle'
                await interaction.response.edit_message(view=self)
                return await self._cog.unshuffle(interaction, quiet=True)

            btn.label = 'Unshuffle'
            await interaction.response.edit_message(view=self)
            return await self._cog.shuffle(interaction, quiet=True)
