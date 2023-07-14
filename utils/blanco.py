from mafic import NodePool, VoiceRegion
from nextcord import Activity, ActivityType, Interaction, PartialMessageable
from nextcord.ext.commands import Bot
from nextcord.ext.tasks import loop
from typing import Any, Dict, Optional, TYPE_CHECKING
from database.database import Database
from utils.jockey_helpers import create_error_embed
from utils.logger import create_logger
from utils.spotify_client import Spotify
from views.now_playing import NowPlayingView
if TYPE_CHECKING:
    from mafic import Node, TrackStartEvent, TrackEndEvent
    from nextcord.abc import Messageable
    from utils.jockey import Jockey


class BlancoBot(Bot):
    """
    Nextcord Bot class, with an integrated Lavalink client.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config = {}

        # Status channels
        self._status_channels: Dict[int, 'Messageable'] = {}

        # Lavalink
        self._pool = NodePool(self)
        self._pool_initialized = False

        # Logger
        self._logger = create_logger(self.__class__.__name__)
    
    @property
    def config(self) -> dict:
        return self._config
    
    @property
    def debug(self) -> bool:
        try:
            debug_guilds = self._config['bot']['debug']['guild_ids']
            return self._config['bot']['debug']['enabled'] and len(debug_guilds) > 0
        except KeyError:
            return False

    @property
    def db(self) -> Database:
        return self._db

    @property
    def pool(self) -> NodePool:
        return self._pool

    @property
    def pool_initialized(self) -> bool:
        return self._pool_initialized
    
    @property
    def spotify(self) -> Spotify:
        return self._spotify_client

    @loop(seconds=3600)
    async def _bot_loop(self):
        activity = Activity(name=f'{len(self.guilds)} servers | /play', type=ActivityType.listening)
        await self.change_presence(activity=activity)

    @_bot_loop.before_loop
    async def _bot_loop_before(self):
        await self.wait_until_ready()
    
    ###################
    # Event listeners #
    ###################

    async def on_ready(self):
        self._logger.info(f'Logged in as {self.user}')
        self.load_extension('cogs')
        if self.debug:
            self._logger.info('Debug mode enabled')
            await self.change_presence(
                activity=Activity(name='/play (debug)', type=ActivityType.listening)
            )
    
    async def on_application_command_error(self, itx: Interaction, error: Exception):
        embed = create_error_embed(str(error))
        
        # Check if we can reply to this interaction
        if itx.response.is_done():
            if isinstance(itx.channel, PartialMessageable):
                await itx.channel.send(embed=embed)
        else:
            await itx.response.send_message(embed=embed)
    
    async def on_node_ready(self, node: 'Node'):
        self._logger.info(f'Connected to Lavalink node `{node.label}\'')

        # Store session ID in database
        if node.session_id is not None:
            self._logger.debug(f'Storing new session ID `{node.session_id}\' for node `{node.label}\'')
            self._db.set_session_id(node.label, node.session_id)
    
    async def on_track_start(self, event: 'TrackStartEvent[Jockey]'):
        # Send now playing embed
        await self.send_now_playing(event)

    async def on_track_end(self, event: 'TrackEndEvent[Jockey]'):
        # Play next track in queue
        self._logger.debug(f'Finished playing {event.track.title} in {event.player.guild.name}')
        if event.player.suppress_skip:
            self._logger.debug('Suppressing autoskip due to previous /skip command')
            event.player.suppress_skip = False
        else:
            await event.player.skip()
    
    def set_status_channel(self, guild_id: int, channel: Optional['Messageable']):
        # If channel is None, remove the status channel
        if channel is None:
            del self._status_channels[guild_id]
            return
        
        self._status_channels[guild_id] = channel
    
    def get_status_channel(self, guild_id: int) -> Optional['Messageable']:
        try:
            return self._status_channels[guild_id]
        except KeyError:
            return None
    
    def init_config(self, config: Dict[str, Any]):
        """
        Initialize the bot with a config.
        """
        self._config = config
        self._db = Database(self._config['bot']['database'])
        self._spotify_client = Spotify(
            client_id=self._config['spotify']['client_id'],
            client_secret=self._config['spotify']['client_secret']
        )
    
    async def init_pool(self):
        """
        Initialize the Lavalink node pool.
        """
        nodes = self._config['lavalink']
        timeout = self._config['bot']['inactivity_timeout']

        # Check that our inactivity timeout is valid
        if not isinstance(timeout, int) or timeout < 1:
            raise ValueError('bot.inactivity_timeout must be an integer greater than 0')

        # Check if the node IDs are unique
        node_ids = [node['id'] for node in nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError('Lavalink node IDs must be unique')

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
                if not isinstance(node['regions'], list):
                    raise TypeError('regions must be a list')
                else:
                    # Try to match regions against enum
                    for region in node['regions']:
                        regions.append(VoiceRegion(region))
                
                # Get session ID from database
                try:
                    session_id = self._db.get_session_id(node['id'])
                except:
                    session_id = None
                    self._logger.debug(f'No session ID `{session_id}\' for node `{node["id"]}\'')
                else:
                    self._logger.debug(f'Using session ID `{session_id}\' for node `{node["id"]}\'')

                await self._pool.create_node(
                    host=node['server'],
                    port=int(node['port']),
                    password=node['password'],
                    regions=regions,
                    resuming_session_id=session_id,
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
    
    async def send_now_playing(self, event: 'TrackStartEvent[Jockey]'):
        guild_id = event.player.guild.id
        channel = self.get_status_channel(guild_id)
        if channel is None:
            raise ValueError(f'Status channel has not been set for guild {guild_id}')

        # Delete last now playing message, if it exists
        last_msg_id = self._db.get_now_playing(guild_id)
        if last_msg_id != -1:
            try:
                last_msg = await channel.fetch_message(last_msg_id)
                await last_msg.delete()
            except:
                pass
        
        # Send now playing embed
        embed = event.player.now_playing()
        view = NowPlayingView(self, event.player)
        msg = await channel.send(embed=embed, view=view)

        # Save now playing message ID
        self._db.set_now_playing(guild_id, msg.id)
