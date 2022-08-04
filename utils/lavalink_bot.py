from lavalink import Client
from nextcord import Activity, ActivityType
from nextcord.ext.commands import Bot
from nextcord.ext.tasks import loop


class LavalinkBot(Bot):
    """
    Nextcord Bot class, with an integrated Lavalink client.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lavalink = None
        self._config = kwargs.get('config', {})
        self._presence_show_servers = False

    @property
    def lavalink(self) -> Client:
        return self._lavalink
    
    @lavalink.setter
    def lavalink(self, value: Client):
        self._lavalink = value
    
    @property
    def config(self) -> dict:
        return self._config
    
    @property
    def debug(self) -> bool:
        try:
            return self.config['bot']['debug']['enabled'] and self.config['bot']['debug']['guild_id']
        except KeyError:
            return False

    @loop(seconds=1800)
    async def _bot_loop(self):
        status = f'{len(self.guilds)} servers | /play' if self._presence_show_servers else '/play'
        activity = Activity(name=status, type=ActivityType.listening)
        await self.change_presence(activity=activity)
        self._presence_show_servers = not self._presence_show_servers

    @_bot_loop.before_loop
    async def _bot_loop_before(self):
        await self.wait_until_ready()
