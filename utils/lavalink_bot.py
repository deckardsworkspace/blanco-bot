from lavalink import Client
from nextcord.ext.commands import Bot


class LavalinkBot(Bot):
    """
    Nextcord Bot class, with an integrated Lavalink client.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lavalink = None
        self._config = kwargs.get('config', {})

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
