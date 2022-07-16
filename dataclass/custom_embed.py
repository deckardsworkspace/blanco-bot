from dataclasses import dataclass, field
from datetime import datetime
from nextcord import Color, Embed, Message
from nextcord.embeds import EmptyEmbed
from nextcord.ext.commands import Context
from typing import List, Union


@dataclass
class CustomEmbed:
    # All optional
    title: str = EmptyEmbed
    color: Color = Color.og_blurple()
    description: Union[str, List[str]] = EmptyEmbed
    fields: List[List[str]] = field(default_factory=list)
    inline_fields: bool = False
    thumbnail_url: str = EmptyEmbed
    image_url: str = EmptyEmbed

    # Header and footer
    header: str = EmptyEmbed
    header_url: str = EmptyEmbed
    header_icon_url: str = EmptyEmbed
    footer: str = EmptyEmbed
    footer_icon_url: str = EmptyEmbed
    timestamp_now: bool = False

    # Create embed
    def __post_init__(self):
        # Can't specify header/footer icons without header/footer names
        if self.header is EmptyEmbed and self.header_icon_url is not EmptyEmbed:
            raise ValueError("Can't specify header icon without header text.")
        if self.footer is EmptyEmbed and self.footer_icon_url is not EmptyEmbed:
            raise ValueError("Can't specify footer icon without footer text.")

        # Create embed object
        description = self.description
        if isinstance(self.description, list):
            description = '\n'.join(list(filter(None, self.description)))
        embed = Embed(title=self.title, description=description, color=self.color)
        
        # Set embed parts
        if self.header is not EmptyEmbed:
            embed.set_author(name=self.header)
        if self.thumbnail_url is not EmptyEmbed and self.thumbnail_url != '':
            embed.set_thumbnail(url=self.thumbnail_url)
        if self.image_url is not EmptyEmbed:
            embed.set_image(url=self.image_url)
        if self.header is not EmptyEmbed:
            embed.set_author(name=self.header, url=self.header_url, icon_url=self.header_icon_url)
        if self.footer is not EmptyEmbed:
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
