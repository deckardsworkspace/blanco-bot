from asyncio import sleep
from nextcord import Embed, Interaction, Message
from typing import Callable, List, Optional
from views.paginator import PaginatorView


class Paginator:
    def __init__(self, itx: Interaction):
        self.current = 0
        self.embeds = []
        self.home = 0
        self.itx = itx
        self.msg: Optional[Message] = None
        self.original_timeout = 0
        self.timeout = 0
    
    async def run(self, embeds: List[Embed], start: int = 0, timeout: int = 0, callback: Callable[[int], None] = None):
        # If there's only one page, just send it as is
        if len(embeds) == 1:
            await self.itx.followup.send(embed=embeds[0])
            if callback is not None:
                callback(msg.id)
                return

        # Based on https://github.com/toxicrecker/DiscordUtils/blob/master/DiscordUtils/Pagination.py
        # but with support for custom home page and adapted for Interaction responses
        timeout = timeout if timeout > 0 else 60
        self.original_timeout = timeout
        self.timeout = timeout

        # Add footer and timestamp to every embed
        for i in range(len(embeds)):
            embeds[i].timestamp = self.itx.created_at
            embeds[i].set_footer(text=f'Page {i + 1} of {len(embeds)}')

        # Send initial embed and call callback with message ID
        self.home = start
        self.current = start
        self.embeds = embeds
        msg = await self.itx.followup.send(embed=self.embeds[start], view=PaginatorView(self))
        self.msg: Message = await msg.channel.fetch_message(msg.id)
        if callback is not None:
            callback(msg.id)
        
        # Remove controls if inactive for more than timeout amount
        while True:
            await sleep(1)
            self.timeout -= 1
            if self.timeout <= 0:
                return await self.msg.edit(view=None)

    async def _switch_page(self, new_page: int) -> Optional[Message]:
        self.current = new_page
        if self.msg is not None:
            try:
                msg = await self.msg.edit(embed=self.embeds[self.current])
            except:
                return None
            else:
                self.timeout = self.original_timeout
                return msg
    
    async def first_page(self):
        await self._switch_page(0)
    
    async def previous_page(self):
        await self._switch_page(self.current - 1)
    
    async def home_page(self):
        await self._switch_page(self.home)
    
    async def next_page(self):
        await self._switch_page(self.current + 1)
    
    async def last_page(self):
        await self._switch_page(len(self.embeds) - 1)
