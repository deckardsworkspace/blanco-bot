from discord.ext.commands import Bot, Cog, command, Context


class PlayerCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        print(f'Loaded {__name__} cog')
    
    @command(name='play', aliases=['p'])
    async def play(self, ctx: Context, *, url: str):
        """Play a song"""
        await ctx.send(f'Playing {url}')
