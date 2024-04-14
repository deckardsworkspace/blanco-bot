"""
Check functions for the music player. These are called before
the player is instantiated, and are used to check if the bot
can connect and play music in a channel.
"""

from typing import TYPE_CHECKING

from nextcord import Interaction, Member

from bot.utils.exceptions import VoiceCommandError

if TYPE_CHECKING:
  from bot.cogs.player.jockey import Jockey


def check_mutual_voice(itx: Interaction, slash: bool = True) -> bool:
  """
  This check ensures that the bot and command author are in the same voice channel.

  :param itx: The interaction object.
  :param slash: Whether this check is being called as part of a slash command. See now_playing.py.
  """

  # Check that the user is in a voice channel in the first place.
  if itx.guild is not None and isinstance(itx.user, Member):
    if not itx.user.voice or not itx.user.voice.channel:
      raise VoiceCommandError('Join a voice channel first.')
  else:
    # Not allowed in DMs
    raise VoiceCommandError('You can only use this command in a server.')

  if itx.application_command is None and not slash:
    raise VoiceCommandError('Abnormal invocation of command. Please try again.')

  player: 'Jockey' = itx.guild.voice_client  # type: ignore
  if player is None and slash:
    assert itx.application_command is not None
    if itx.application_command.name == 'play':
      # The /play command causes the bot to connect to voice,
      # so we don't have to worry about the rest of the checks here.
      return True
    raise VoiceCommandError('Please `/play` something first before using this command.')

  voice_channel = itx.user.voice.channel
  if not player.is_connected():
    # Bot needs to already be in voice channel to pause, unpause, skip etc.
    if itx.application_command is not None and itx.application_command.name != 'play':
      raise VoiceCommandError("I'm not connected to voice.")

    # Bot needs to have permissions to connect to voice.
    permissions = voice_channel.permissions_for(itx.guild.me)
    if not permissions.connect or not permissions.speak:
      raise VoiceCommandError(
        'I need the `CONNECT` and `SPEAK` permissions to play music.'
      )

    # Bot needs to connect to a channel that isn't full.
    if voice_channel.user_limit and voice_channel.user_limit <= len(
      voice_channel.members
    ):
      raise VoiceCommandError('Your voice channel is full.')
  elif int(player.channel.id) != voice_channel.id:  # type: ignore
    raise VoiceCommandError('You need to be in my voice channel.')

  return True
