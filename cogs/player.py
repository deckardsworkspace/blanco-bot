from discord.ext.commands import Cog, command, Context
from lavalink import add_event_hook, DefaultPlayer
from lavalink.events import *
from typing import Optional
from utils.database import Database
from utils.lavalink import init_lavalink
from utils.lavalink_bot import LavalinkBot


class PlayerCog(Cog):
    def __init__(self, bot: LavalinkBot, db: Database):
        self.bot = bot
        self.db = db

        # Create Lavalink client instance
        if not hasattr(bot, 'lavalink'):
            bot.lavalink = init_lavalink(bot.user.id)

        # Listen to Lavalink events
        add_event_hook(self.on_lavalink_event)

        print(f'Loaded cog: {self.__class__.__name__}')
    
    async def on_lavalink_event(self, event: Event):
        pass

    async def get_player(self, guild_id: int) -> Optional[DefaultPlayer]:
        """
        Get the player for a guild.
        """
        return self.bot.lavalink.player_manager.get(guild_id)
    
    @command(name='play', aliases=['p'])
    async def play(self, ctx: Context, *, url: str):
        """Play a song"""
        await ctx.send(f'Playing {url}')
