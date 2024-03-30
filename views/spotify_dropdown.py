"""
View for the `/playlists` command, which contains a dropdown menu for selecting
a Spotify playlist.
"""

from typing import TYPE_CHECKING, List

from nextcord import Colour, SelectOption
from nextcord.ui import Select, View

from dataclass.custom_embed import CustomEmbed

if TYPE_CHECKING:
  from nextcord import Interaction

  from cogs.player import PlayerCog
  from dataclass.spotify import SpotifyResult
  from utils.blanco import BlancoBot


MAX_LINE_LENGTH = 100


class SpotifyDropdown(Select):
  """
  Dropdown menu for selecting a Spotify entity.
  """

  def __init__(
    self,
    bot: 'BlancoBot',
    choices: List['SpotifyResult'],
    user_id: int,
    entity_type: str,
  ):
    self._cog: 'PlayerCog' = bot.get_cog('PlayerCog')  # type: ignore
    self._user_id = user_id
    self._choices = {x.spotify_id: x.name for x in choices}
    self._type = entity_type

    # Create options
    options = []
    for choice in choices:
      # Truncate names to 100 characters
      choice_name = choice.name
      if len(choice_name) > MAX_LINE_LENGTH:
        choice_name = choice_name[:97] + '...'
      elif len(choice_name) == 0:
        # Some playlists have empty names, for example:
        # https://open.spotify.com/playlist/6HlbMZPay5jlI7KWA0Mwyu
        choice_name = '(no name)'

      # Truncate descriptions to 100 characters
      choice_desc = choice.description
      if len(choice_desc) > MAX_LINE_LENGTH:
        choice_desc = choice_desc[:97] + '...'

      options.append(
        SelectOption(
          label=choice_name, description=choice_desc, value=choice.spotify_id
        )
      )

    super().__init__(
      placeholder=f'Choose {entity_type}...',
      options=options,
      min_values=1,
      max_values=1,
    )

  async def callback(self, interaction: 'Interaction'):
    """
    Callback for the dropdown menu. Calls the `/play` command with the
    selected entity.
    """
    # Ignore if the user isn't the one who invoked the command
    if not interaction.user or interaction.user.id != self._user_id:
      return

    # Edit message
    entity_id = self.values[0]
    entity_url = f'https://open.spotify.com/{self._type}/{entity_id}'
    if interaction.message:
      embed = CustomEmbed(
        color=Colour.yellow(),
        title=':hourglass:｜Loading...',
        description=f'Selected {self._type} [{self._choices[entity_id]}]({entity_url}).',
      )
      await interaction.message.edit(embed=embed.get(), view=None)

    # Call the `/play` command with the entity URL
    await self._cog.play(interaction, query=entity_url)

    # Delete message
    if interaction.message:
      await interaction.message.delete()


class SpotifyDropdownView(View):
  """
  View for the `/playlists` command, which contains a dropdown menu for selecting
  a Spotify entity.
  """

  def __init__(
    self,
    bot: 'BlancoBot',
    playlists: List['SpotifyResult'],
    user_id: int,
    entity_type: str,
  ):
    super().__init__(timeout=None)

    self.add_item(SpotifyDropdown(bot, playlists, user_id, entity_type))
