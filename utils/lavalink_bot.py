from lavalink import Client
from nextcord import Activity, ActivityType
from nextcord.ext.commands import Bot
from nextcord.ext.tasks import loop
from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from .jockey import Jockey


class LavalinkBot(Bot):
    """
    Nextcord Bot class, with an integrated Lavalink client.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config = {}
        self._jockeys: Dict[int, 'Jockey'] = {}
        self._lavalink = None

    @property
    def lavalink(self) -> Client:
        return self._lavalink
    
    @lavalink.setter
    def lavalink(self, value: Client):
        self._lavalink = value
    
    @property
    def config(self) -> dict:
        return self._config
    
    @config.setter
    def config(self, value: dict):
        self._config = value
    
    @property
    def debug(self) -> bool:
        try:
            return self.config['bot']['debug']['enabled'] and self.config['bot']['debug']['guild_id']
        except KeyError:
            return False

    @property
    def jockeys(self) -> dict:
        return self._jockeys

    @loop(seconds=3600)
    async def _bot_loop(self):
        activity = Activity(name=f'{len(self.guilds)} servers | /play', type=ActivityType.listening)
        await self.change_presence(activity=activity)

    @_bot_loop.before_loop
    async def _bot_loop_before(self):
        await self.wait_until_ready()
