"""
Dataclass for an instance of nextcord.Embed with convenience fields
for the timestamp, multiline description, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Union

from nextcord import Colour, Embed


@dataclass
class CustomEmbed:
    """
    Dataclass for an instance of nextcord.Embed with convenience fields
    for the timestamp, multiline description, etc.
    """
    # All optional
    title: Optional[str] = None
    color: Colour = Colour.og_blurple()
    description: Optional[Union[str, List[str]]] = None
    fields: List[List[str]] = field(default_factory=list)
    inline_fields: bool = False
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None

    # Header and footer
    header: Optional[str] = None
    header_url: Optional[str] = None
    header_icon_url: Optional[str] = None
    footer: Optional[str] = None
    footer_icon_url: Optional[str] = None
    timestamp_now: bool = False

    # Create embed
    def __post_init__(self):
        # Can't specify header/footer icons without header/footer names
        if self.header is None and self.header_icon_url is not None:
            raise ValueError("Can't specify header icon without header text.")
        if self.footer is None and self.footer_icon_url is not None:
            raise ValueError("Can't specify footer icon without footer text.")

        # Create embed object
        description = self.description
        if isinstance(self.description, list):
            description = '\n'.join(list(filter(None, self.description)))
        embed = Embed(title=self.title, description=description, color=self.color)

        # Set embed parts
        if self.header is not None:
            embed.set_author(name=self.header)
        if self.thumbnail_url is not None and self.thumbnail_url != '':
            embed.set_thumbnail(url=self.thumbnail_url)
        if self.image_url is not None:
            embed.set_image(url=self.image_url)
        if self.header is not None:
            embed.set_author(name=self.header, url=self.header_url, icon_url=self.header_icon_url)
        if self.footer is not None:
            embed.set_footer(text=self.footer, icon_url=self.footer_icon_url)
        if len(self.fields) > 0:
            for f in self.fields: # pylint: disable=invalid-name
                embed.add_field(name=f[0], value=f[1], inline=self.inline_fields)

        # Save embed
        self.embed = embed

    # Get embed object
    def get(self) -> Embed:
        """
        Get the resulting nextcord.Embed object.
        """
        # Add timestamp to embed
        if self.timestamp_now:
            self.embed.timestamp = datetime.now()

        return self.embed
