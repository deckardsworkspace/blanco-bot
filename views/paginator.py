"""
View for the Paginator. See utils/paginator.py for more information.
"""

from typing import TYPE_CHECKING

from nextcord import ButtonStyle
from nextcord.ui import View, button

if TYPE_CHECKING:
    from nextcord import Interaction
    from nextcord.ui import Button


class PaginatorView(View):
    """
    Controls for the Paginator. See utils/paginator.py for more information.
    """
    def __init__(self, paginator, timeout: int = 60):
        super().__init__(timeout=None)
        self.paginator = paginator

    @button(label='⏮️', style=ButtonStyle.grey)
    async def first_page(self, _b: 'Button', _i: 'Interaction'):
        """
        Go to the first page.
        """
        return await self.paginator.first_page()

    @button(label='⏪', style=ButtonStyle.grey)
    async def previous_page(self, _b: 'Button', _i: 'Interaction'):
        """
        Go to the previous page.
        """
        return await self.paginator.previous_page()

    @button(label='🏠', style=ButtonStyle.grey)
    async def home_page(self, _b: 'Button', _i: 'Interaction'):
        """
        Go to the home page.
        """
        return await self.paginator.home_page()

    @button(label='⏩', style=ButtonStyle.grey)
    async def next_page(self, _b: 'Button', _i: 'Interaction'):
        """
        Go to the next page.
        """
        return await self.paginator.next_page()

    @button(label='⏭️', style=ButtonStyle.grey)
    async def last_page(self, _b: 'Button', _i: 'Interaction'):
        """
        Go to the last page.
        """
        return await self.paginator.last_page()
