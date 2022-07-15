from discord.ext.commands import Cog, command, Context
from lavalink import add_event_hook
from typing import get_args, Optional
from utils.database import Database
from utils.jockey import Jockey
from utils.lavalink import EventWithPlayer, init_lavalink
from utils.lavalink_bot import LavalinkBot


class PlayerCog(Cog):
    def __init__(self, bot: LavalinkBot, db: Database):
        self.bot = bot
        self.db = db

        # Jockey instances
        self._jockeys = {}

        # Create Lavalink client instance
        if bot.lavalink == None:
            bot.lavalink = init_lavalink(bot.user.id)

        # Listen to Lavalink events
        add_event_hook(self.on_lavalink_event)

        print(f'Loaded cog: {self.__class__.__name__}')
    
    async def on_lavalink_event(self, event: EventWithPlayer):
        # Does the event have a player attribute?
        if isinstance(event, get_args(EventWithPlayer)):
            # Dispatch event to appropriate jockey
            guild_id = event.player.guild_id
            if event.player.guild_id in self._jockeys:
                await self._jockeys[guild_id].handle_event(event)
        else:
            # Must be either a NodeConnectedEvent or a NodeDisconnectedEvent.
            print(event)

    @command(name='play', aliases=['p'])
    async def play(self, ctx: Context, *, query: Optional[str] = None):
        """Play a song"""
        async with ctx.typing():
            # Create jockey for guild if it doesn't exist yet
            if ctx.guild.id not in self._jockeys:
                player = self.bot.lavalink.player_manager.create(ctx.guild.id)
                self._jockeys[ctx.guild.id] = Jockey(self.bot, self.db, player, ctx.message.channel)
