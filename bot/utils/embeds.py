"""
Success and error embeds for the bot.
"""

from typing import Optional

from nextcord import Colour, Embed

from bot.models.custom_embed import CustomEmbed


def create_error_embed(message: str) -> Embed:
  """
  Create an error embed.
  """
  embed = CustomEmbed(color=Colour.red(), title=':x:｜Error', description=message)
  return embed.get()


def create_success_embed(
  title: Optional[str] = None, body: Optional[str] = None
) -> Embed:
  """
  Create a success embed.
  """
  if body is None:
    if title is None:
      raise ValueError('Either title or body must be specified')

    body = title
    title = 'Success'

  embed = CustomEmbed(
    color=Colour.green(), title=f':white_check_mark:｜{title}', description=body
  )
  return embed.get()
