from nextcord import ButtonStyle, Interaction
from nextcord.ui import button, Button, View

class PaginatorView(View):
    def __init__(self, paginator, timeout: int = 60):
        super().__init__(timeout=None)
        self.paginator = paginator
    
    @button(label='⏮️', style=ButtonStyle.grey)
    async def first_page(self, _: Button, interaction: Interaction):
        return await self.paginator.first_page()
    
    @button(label='⏪', style=ButtonStyle.grey)
    async def previous_page(self, _: Button, interaction: Interaction):
        return await self.paginator.previous_page()
    
    @button(label='🏠', style=ButtonStyle.grey)
    async def home_page(self, _: Button, interaction: Interaction):
        return await self.paginator.previous_page()

    @button(label='⏩', style=ButtonStyle.grey)
    async def next_page(self, _: Button, interaction: Interaction):
        return await self.paginator.next_page()

    @button(label='⏭️', style=ButtonStyle.grey)
    async def last_page(self, _: Button, interaction: Interaction):
        return await self.paginator.last_page()
        