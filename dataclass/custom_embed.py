from dataclasses import dataclass, field
from datetime import datetime
from nextcord import Color, Embed, Message
from nextcord.ext.commands import Context
from typing import List, Optional, Union


@dataclass
class CustomEmbed:
    # All optional
    title: Optional[str] = None
    color: Color = Color.og_blurple()
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
        if len(self.fields):
            for field in self.fields:
                embed.add_field(name=field[0], value=field[1], inline=self.inline_fields)

        # Save embed
        self.embed = embed
    
    # Get embed object
    def get(self) -> Embed:
        # Add timestamp to embed
        if self.timestamp_now:
            self.embed.timestamp = datetime.now()

        return self.embed
        
    # Send embed
    async def send(self, ctx: Context, as_reply: bool = False) -> Message:
        # Add timestamp to embed
        if self.timestamp_now:
            self.embed.timestamp = datetime.now()
        else:
            self.embed.timestamp = ctx.message.created_at

        if as_reply:
            return await ctx.reply(embed=self.embed)
        return await ctx.send(embed=self.embed)
