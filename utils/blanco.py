from database import Database
from logging import INFO
from mafic import EndReason, NodePool, VoiceRegion
from nextcord import Activity, ActivityType, Interaction, PartialMessageable, TextChannel, Thread, VoiceChannel
from nextcord.ext.commands import Bot
from nextcord.ext.tasks import loop
from typing import Dict, Optional, TYPE_CHECKING, Union
from utils.exceptions import EndOfQueueError
from utils.jockey_helpers import create_error_embed
from utils.logger import create_logger
from utils.spotify_client import Spotify
from views.now_playing import NowPlayingView
if TYPE_CHECKING:
    from dataclass.config import Config
    from logging import Logger
    from mafic import Node, TrackStartEvent, TrackEndEvent
    from utils.jockey import Jockey


StatusChannel = Union[PartialMessageable, VoiceChannel, TextChannel, Thread]


class BlancoBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Optional['Config'] = None
        self._db: Optional[Database] = None

        # Status channels
        self._status_channels: Dict[int, 'StatusChannel'] = {}

        # Lavalink
        self._pool = NodePool(self)
        self._pool_initialized = False

        # Loggers
        self._logger = create_logger(self.__class__.__name__, debug=True)
        self._jockey_logger = create_logger('jockey', debug=True)
    
    @property
    def config(self) -> Optional['Config']:
        return self._config
    
    @property
    def debug(self) -> bool:
        if self._config is None or self._config.debug_guild_ids is None:
            return False
        return self._config.debug_enabled and len(self._config.debug_guild_ids) > 0

    @property
    def db(self) -> Database:
        if self._db is None:
            raise RuntimeError('Database has not been initialized')
        return self._db
    
    @property
    def jockey_logger(self) -> 'Logger':
        return self._jockey_logger

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
            self._logger.warn('Debug mode enabled')
            await self.change_presence(
                activity=Activity(name='/play (debug)', type=ActivityType.listening)
            )

            # Sync commands with debug guilds
            if self._config is not None and self._config.debug_guild_ids is not None:
                for guild in self._config.debug_guild_ids:
                    self._logger.info(f'Syncing commands for debug guild {guild}')
                    await self.sync_application_commands(guild_id=guild)
                self._logger.info(f'Synced commands for {len(self._config.debug_guild_ids)} guild(s)!')
        else:
            # Sync commands
            self._logger.info('Syncing global commands...')
            await self.sync_application_commands()
            self._logger.info('Synced commands!')
    
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
            self.db.set_session_id(node.label, node.session_id)
    
    async def on_track_start(self, event: 'TrackStartEvent[Jockey]'):
        try:
            # Send now playing embed
            await self.send_now_playing(event)
        except EndOfQueueError:
            self._logger.warn(f'Got track_start event for idle player in {event.player.guild.name}')

    async def on_track_end(self, event: 'TrackEndEvent[Jockey]'):
        if event.reason == EndReason.REPLACED:
            self._logger.debug(f'Skipped `{event.track.title}\' in {event.player.guild.name}')
        elif event.reason == EndReason.FINISHED:
            # Play next track in queue
            self._logger.debug(f'Finished playing `{event.track.title}\' in {event.player.guild.name}')
            await event.player.skip()
        elif event.reason == EndReason.STOPPED:
            self._logger.info(f'Stopped player in {event.player.guild.name}')
        else:
            self._logger.error(f'Unhandled {event.reason} in {event.player.guild.name} for `{event.track.title}\'')
    
    def set_status_channel(self, guild_id: int, channel: 'StatusChannel'):
        # If channel is None, remove the status channel
        if channel is None:
            del self._status_channels[guild_id]
        
        self._status_channels[guild_id] = channel
        try:
            self.db.set_status_channel(guild_id, -1 if channel is None else channel.id)
        except:
            self._logger.warn(f'Failed to save status channel for guild {guild_id} in DB')
        
    def get_status_channel(self, guild_id: int) -> Optional['StatusChannel']:
        # Check if status channel is cached
        if guild_id in self._status_channels:
            return self._status_channels[guild_id]
        
        # Get status channel ID from database
        channel_id = -1
        try:
            channel_id = self.db.get_status_channel(guild_id)
        except:
            self._logger.warn(f'Failed to get status channel ID for guild {guild_id} from DB')

        # Get status channel from ID
        if channel_id != -1:
            channel = self.get_channel(channel_id)
            if channel is None:
                self._logger.error(f'Failed to get status channel for guild {guild_id}')
            elif not isinstance(channel, StatusChannel):
                self._logger.error(f'Status channel for guild {guild_id} is not Messageable')
            else:
                self._status_channels[guild_id] = channel
                return channel
        
        return None
        
    def init_config(self, config: 'Config'):
        """
        Initialize the bot with a config.
        """
        self._config = config
        
        # Change log level if needed
        if not self.debug:
            self._logger.setLevel(INFO)
            self._jockey_logger.setLevel(INFO)

        self._db = Database(config.db_file)
        self._spotify_client = Spotify(
            client_id=config.spotify_client_id,
            client_secret=config.spotify_client_secret
        )
    
    async def init_pool(self):
        """
        Initialize the Lavalink node pool.
        """
        if self._config is None:
            raise RuntimeError('Cannot initialize Lavalink without a config')
        nodes = self._config.lavalink_nodes

        # Add local node
        for node in nodes.values():
            # Try to match regions against enum
            regions = []
            for region in node.regions:
                regions.append(VoiceRegion(region))
            
            # Get session ID from database
            try:
                session_id = self.db.get_session_id(node.id)
            except:
                session_id = None
                self._logger.debug(f'No session ID for node `{node.id}\'')
            else:
                self._logger.debug(f'Using session ID `{session_id}\' for node `{node.id}\'')

            await self._pool.create_node(
                host=node.host,
                port=node.port,
                password=node.password,
                regions=regions,
                resuming_session_id=session_id,
                label=node.id,
                secure=node.secure
            )

        self._pool_initialized = True
    
    async def send_now_playing(self, event: 'TrackStartEvent[Jockey]'):
        guild_id = event.player.guild.id
        channel = self.get_status_channel(guild_id)
        if channel is None:
            raise ValueError(f'Status channel has not been set for guild {guild_id}')

        # Delete last now playing message, if it exists
        last_msg_id = self.db.get_now_playing(guild_id)
        if last_msg_id != -1:
            try:
                last_msg = await channel.fetch_message(last_msg_id)
                await last_msg.delete()
            except:
                pass
        
        # Send now playing embed
        embed = event.player.now_playing(event.track)
        view = NowPlayingView(self, event.player)
        msg = await channel.send(embed=embed, view=view)

        # Save now playing message ID
        self.db.set_now_playing(guild_id, msg.id)
