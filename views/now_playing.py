"""
Now Playing view for the player.
"""

from typing import TYPE_CHECKING, Optional

from nextcord import ButtonStyle
from nextcord.ui import Button, View, button
from requests.exceptions import HTTPError, Timeout

from utils.constants import SPOTIFY_403_ERR_MSG
from utils.embeds import create_error_embed, create_success_embed
from utils.exceptions import VoiceCommandError
from utils.player_checks import check_mutual_voice

if TYPE_CHECKING:
    from nextcord import Interaction

    from cogs.player import PlayerCog
    from cogs.player.jockey import Jockey
    from utils.blanco import BlancoBot


class ShuffleButton(Button):
    """
    Shuffle button for the Now Playing view.
    """
    def __init__(self, init_state: bool = False):
        """
        Initialize the shuffle button.

        :param init_state: Initial state of the shuffle button.
            True if the queue is shuffled, False otherwise.
        """
        super().__init__(
            style=ButtonStyle.grey,
            label='Unshuffle' if init_state else 'Shuffle'
        )

    async def callback(self, interaction: 'Interaction'):
        """
        Toggle shuffle on the current queue.
        """
        assert self.view is not None
        view: NowPlayingView = self.view

        if await view.check_mutual_voice(interaction):
            status = view.player.queue_manager.is_shuffling
            self.label = 'Shuffle' if status else 'Unshuffle'
            await interaction.response.edit_message(view=view)

            # Shuffle or unshuffle
            if status:
                return await view.cog.unshuffle(interaction, quiet=True)
            return await view.cog.shuffle(interaction, quiet=True)


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

        # Add shuffle button
        self.add_item(ShuffleButton(player.queue_manager.is_shuffling))

    @property
    def cog(self) -> 'PlayerCog':
        """
        Return the PlayerCog that this View was created by.
        """
        return self._cog

    @property
    def player(self) -> 'Jockey':
        """
        Return the player that this View is bound to.
        """
        return self._player

    async def check_mutual_voice(self, interaction: 'Interaction') -> bool:
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
        if await self.check_mutual_voice(interaction):
            return await self._cog.queue(interaction)

    @button(label='⏮️', style=ButtonStyle.grey)
    async def skip_backward(self, _: 'Button', interaction: 'Interaction'):
        """
        Skip to the previous track.
        """
        if await self.check_mutual_voice(interaction):
            return await self._cog.previous(interaction)

    @button(label='⏸️', style=ButtonStyle.blurple)
    async def toggle_pause(self, btn: 'Button', interaction: 'Interaction'):
        """
        Toggle pause on the current track.
        """
        if await self.check_mutual_voice(interaction):
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
        if await self.check_mutual_voice(interaction):
            return await self._cog.skip(interaction)

    @button(label='⏹️', style=ButtonStyle.red)
    async def stop_player(self, _: 'Button', interaction: 'Interaction'):
        """
        Stop the player.
        """
        if await self.check_mutual_voice(interaction):
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
        except HTTPError as err:
            if err.response is not None:
                if err.response.status_code == 403:
                    message = SPOTIFY_403_ERR_MSG.format('Like this track')
                else:
                    message = ''.join([
                        f'**Error {err.response.status_code}** while trying to Like this track.',
                        'Please try again later.\n',
                        f'```\n{err}```'
                    ])
            else:
                message = ''.join([
                    'Error while trying to Like this track.',
                    'Please try again later.\n',
                    f'```\n{err}```'
                ])

            return await interaction.followup.send(
                embed=create_error_embed(message),
                ephemeral=True
            )
        except Timeout as err:
            return await interaction.followup.send(
                embed=create_error_embed('\n'.join([
                    'Timed out while trying to Like this track.',
                    'Please try again later.\n',
                    f'```{err}```'
                ])),
                ephemeral=True
            )

        # Send response
        return await interaction.followup.send(
            embed=create_success_embed('Added to your Liked Songs.'),
            ephemeral=True
        )
