import mafic
from nextcord import Activity, ActivityType
from nextcord.ext.commands import Bot
from nextcord.ext.tasks import loop
from typing import Dict, List, TYPE_CHECKING
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
        self._pool = mafic.NodePool(self)
        self._pool_initialized = False

    @property
    def pool(self) -> mafic.NodePool:
        return self._pool

    @property
    def pool_initialized(self) -> bool:
        return self._pool_initialized
    
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
    def jockeys(self) -> Dict[int, 'Jockey']:
        return self._jockeys

    @loop(seconds=3600)
    async def _bot_loop(self):
        activity = Activity(name=f'{len(self.guilds)} servers | /play', type=ActivityType.listening)
        await self.change_presence(activity=activity)

    @_bot_loop.before_loop
    async def _bot_loop_before(self):
        await self.wait_until_ready()
    
    async def init_pool(self):
        """
        Initialize the Lavalink node pool.
        """
        nodes = self.config['lavalink']
        timeout = self.config['bot']['inactivity_timeout']

        # Check that our inactivity timeout is valid
        if not isinstance(timeout, int) or timeout < 1:
            raise ValueError('bot.inactivity_timeout must be an integer greater than 0')

        # Add local node
        for i, node in enumerate(nodes):
            try:
                # Check if host, password, and label are strings
                if not isinstance(node['server'], str):
                    raise TypeError('server must be a string')
                if not isinstance(node['password'], str):
                    raise TypeError('password must be a string')
                if not isinstance(node['id'], str):
                    raise TypeError('id must be a string')
                
                # Check if port is an int
                if not isinstance(node['port'], int):
                    raise TypeError('port must be an int')
                
                # Check if ssl is a bool
                if not isinstance(node['ssl'], bool):
                    raise TypeError('ssl must be a bool')
                
                # Check if region is a list
                regions = []
                if not isinstance(node['region'], list):
                    raise TypeError('region must be a list')
                else:
                    # Try to match regions against enum
                    for region in node['region']:
                        regions.append(mafic.VoiceRegion(region))

                await self._pool.create_node(
                    host=node['server'],
                    port=int(node['port']),
                    password=node['password'],
                    regions=regions,
                    resuming_session_id=node['id'],
                    timeout=timeout,
                    label=node['id'],
                    secure=node['ssl']
                )
            except KeyError as e:
                raise RuntimeError(f'Missing key in config for Lavalink node {i}: {e.args[0]}')
            except TypeError as e:
                raise RuntimeError(f'Wrong value type in config for Lavalink node {i}: {e.args[0]}')
            except ValueError as e:
                raise RuntimeError(f'Invalid value in config for Lavalink node {i}: {e.args[0]}')

        self._pool_initialized = True
