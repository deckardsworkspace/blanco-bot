"""
Custom bot class for Blanco.
"""

from logging import INFO
from sqlite3 import OperationalError
from typing import TYPE_CHECKING, Dict, Optional, Union

from asyncio import get_event_loop
from mafic import EndReason, NodePool, VoiceRegion
from nextcord import (Activity, ActivityType, Forbidden, HTTPException,
                      Interaction, NotFound, PartialMessageable, TextChannel,
                      Thread, VoiceChannel)
from nextcord.ext.commands import Bot

from cogs.player.jockey import find_lavalink_track
from database import Database
from views.now_playing import NowPlayingView

from .embeds import create_error_embed
from .exceptions import EndOfQueueError
from .logger import create_logger
from .scrobbler import Scrobbler
from .spotify_client import Spotify
from .spotify_private import PrivateSpotify

if TYPE_CHECKING:
    from logging import Logger

    from mafic import Node, TrackEndEvent, TrackStartEvent

    from cogs.player.jockey import Jockey
    from dataclass.config import Config


StatusChannel = Union[PartialMessageable, VoiceChannel, TextChannel, Thread]


class BlancoBot(Bot):
    """
    Custom bot class for Blanco.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Optional['Config'] = None
        self._db: Optional[Database] = None

        # Status channels
        self._status_channels: Dict[int, 'StatusChannel'] = {}

        # Spotify client
        self._spotify_client: Optional[Spotify] = None

        # Lavalink
        self._pool = NodePool(self)
        self._pool_initialized = False

        # Loggers
        self._logger = create_logger(self.__class__.__name__, debug=True)
        self._jockey_logger = create_logger('jockey', debug=True)

        # Scrobblers and private Spotify clients per user
        self._scrobblers: Dict[int, 'Scrobbler'] = {}
        self._scrobbler_logger = create_logger('scrobbler', debug=True)
        self._spotify_clients: Dict[int, PrivateSpotify] = {}

    @property
    def config(self) -> Optional['Config']:
        """
        Gets the bot's config.
        """
        return self._config

    @property
    def debug(self) -> bool:
        """
        Gets whether debug mode is enabled.
        """
        if self._config is None or self._config.debug_guild_ids is None:
            return False
        return self._config.debug_enabled and len(self._config.debug_guild_ids) > 0

    @property
    def database(self) -> Database:
        """
        Gets the bot's database.
        """
        if self._db is None:
            raise RuntimeError('Database has not been initialized')
        return self._db

    @property
    def jockey_logger(self) -> 'Logger':
        """
        Gets the bot's reusable logger for all Jockey instances.
        """
        return self._jockey_logger

    @property
    def pool(self) -> NodePool:
        """
        Gets the bot's Lavalink node pool.
        """
        return self._pool

    @property
    def pool_initialized(self) -> bool:
        """
        Gets whether the Lavalink node pool has been initialized.
        """
        return self._pool_initialized

    @property
    def spotify(self) -> Spotify:
        """
        Gets the bot's Spotify client. See utils/spotify_client.py.
        """
        if self._spotify_client is None:
            raise RuntimeError('Spotify client has not been initialized')
        return self._spotify_client

    ###################
    # Event listeners #
    ###################

    async def on_ready(self):
        """
        Called when the bot is ready.
        """
        self._logger.info('Logged in as %s', self.user)
        self.load_extension('cogs')
        self.load_extension('server')

        if self.debug:
            self._logger.warning('Debug mode enabled')
            await self.change_presence(
                activity=Activity(name='/play (debug)', type=ActivityType.listening)
            )

            # Sync commands with debug guilds
            if self._config is not None and self._config.debug_guild_ids is not None:
                for guild in self._config.debug_guild_ids:
                    self._logger.info('Syncing commands for debug guild %d', guild)
                    await self.sync_application_commands(guild_id=guild)
                self._logger.info(
                    'Synced commands for %d guild(s)!',
                    len(self._config.debug_guild_ids)
                )
        else:
            await self.change_presence(
                activity=Activity(name='/play', type=ActivityType.listening)
            )

            # Sync commands
            self._logger.info('Syncing global commands...')
            await self.sync_application_commands()
            self._logger.info('Synced commands!')

    async def on_application_command_error(self, itx: Interaction, error: Exception):
        """
        Called when an error occurs while processing an interaction.
        """
        embed = create_error_embed(str(error))

        # Check if we can reply to this interaction
        if itx.response.is_done():
            if isinstance(itx.channel, PartialMessageable):
                await itx.channel.send(embed=embed)
        else:
            await itx.response.send_message(embed=embed)

    async def on_node_ready(self, node: 'Node'):
        """
        Called when a Lavalink node is connected and ready.
        """
        self._logger.info('Connected to Lavalink node `%s\'', node.label)

        # Store session ID in database
        if node.session_id is not None:
            old_id = self.database.get_session_id(node.label)
            if old_id is not None and old_id != node.session_id:
                self._logger.debug(
                    'Replacing old session ID `%s\' for node `%s\'',
                    old_id,
                    node.label
                )
            self.database.set_session_id(node.label, node.session_id)

    async def on_track_start(self, event: 'TrackStartEvent[Jockey]'):
        """
        Called when a track starts playing.
        """
        self._logger.info(
            'Started playing `%s\' in %s',
            event.track.title,
            event.player.guild.name
        )

        # Send now playing embed
        try:
            await self.send_now_playing(event)
        except EndOfQueueError:
            self._logger.warning(
                'Got track_start event for idle player in %s',
                event.player.guild.name
            )
            return

        # Find Lavalink track for next track in queue
        curr_i = event.player.current_index
        if event.player.is_shuffling:
            next_shuf_i = event.player.shuffle_indices.index(curr_i) + 1
            next_i = event.player.shuffle_indices[next_shuf_i]
        else:
            next_i = curr_i + 1
        if next_i < len(event.player.queue):
            next_track = event.player.queue[next_i]
            if next_track.lavalink_track is not None:
                # Track has already been matched
                return

            self._logger.debug(
                'Matching track `%s\' in the background',
                next_track.title
            )

            # Check if Deezer is enabled
            assert self._config is not None
            deezer_enabled = self._config.lavalink_nodes[event.player.node.label].deezer

            get_event_loop().create_task(find_lavalink_track(
                node=event.player.node,
                item=next_track,
                deezer_enabled=deezer_enabled,
                in_place=True
            ))

    async def on_track_end(self, event: 'TrackEndEvent[Jockey]'):
        """
        Called when a track ends.
        """
        if event.reason == EndReason.REPLACED:
            self._logger.warning(
                'Skipped `%s\' in %s',
                event.track.title,
                event.player.guild.name
            )
        elif event.reason == EndReason.FINISHED:
            # Play next track in queue
            self._logger.info(
                'Finished playing `%s\' in %s',
                event.track.title,
                event.player.guild.name
            )
            await event.player.skip()
        elif event.reason == EndReason.STOPPED:
            self._logger.info(
                'Stopped player in %s',
                event.player.guild.name
            )
        elif event.reason == EndReason.LOAD_FAILED:
            self._logger.critical(
                'Failed to load `%s\' in %s',
                event.track.title,
                event.player.guild.name
            )
        else:
            self._logger.error(
                'Unhandled %s in %s for `%s\'',
                event.reason,
                event.player.guild.name,
                event.track.title
            )

    #####################
    # Utility functions #
    #####################

    def get_scrobbler(self, user_id: int) -> Optional['Scrobbler']:
        """
        Gets a Last.fm scrobbler instance for the specified user.
        """
        assert self._config is not None and self._db is not None

        # Check if user is authenticated with Last.fm
        creds = self._db.get_lastfm_credentials(user_id)
        if creds is None:
            if user_id in self._scrobblers:
                # User must have unlinked their account, so delete the cached scrobbler
                del self._scrobblers[user_id]

            return None

        # Check if a scrobbler already exists
        if user_id not in self._scrobblers:
            # Create scrobbler
            self._scrobblers[user_id] = Scrobbler(self._config, creds, self._scrobbler_logger)

        return self._scrobblers[user_id]

    def get_spotify_client(self, user_id: int) -> Optional[PrivateSpotify]:
        """
        Gets a Spotify client instance for the specified user.
        """
        assert self._config is not None and self._db is not None

        # Try to get credentials
        creds = self._db.get_oauth('spotify', user_id)
        if creds is None:
            # Check if there is a cached client for this user
            if user_id in self._spotify_clients:
                # User must have unlinked their account, so delete the cached client
                del self._spotify_clients[user_id]

            raise ValueError(f'Please link your Spotify account [here.]({self._config.base_url})')

        # Check if a client already exists
        if user_id not in self._spotify_clients:
            self._spotify_clients[user_id] = PrivateSpotify(
                config=self._config,
                database=self._db,
                credentials=creds
            )
            self._logger.debug('Created Spotify client for user %d', user_id)

        return self._spotify_clients[user_id]

    def set_status_channel(self, guild_id: int, channel: 'StatusChannel'):
        """
        Sets the status channel for the specified guild, which is used to send
        now playing messages and announcements.
        """
        # If channel is None, remove the status channel
        if channel is None:
            del self._status_channels[guild_id]

        self._status_channels[guild_id] = channel
        self.database.set_status_channel(guild_id, -1 if channel is None else channel.id)

    def get_status_channel(self, guild_id: int) -> Optional['StatusChannel']:
        """
        Gets the status channel for the specified guild.
        """
        # Check if status channel is cached
        if guild_id in self._status_channels:
            return self._status_channels[guild_id]

        # Get status channel ID from database
        channel_id = -1
        try:
            channel_id = self.database.get_status_channel(guild_id)
        except OperationalError:
            self._logger.warning(
                'Failed to get status channel ID for guild %d from database',
                guild_id
            )

        # Get status channel from ID
        if channel_id != -1:
            channel = self.get_channel(channel_id)
            if channel is None:
                self._logger.error(
                    'Failed to get status channel for guild %d',
                    guild_id
                )
            elif not isinstance(channel, StatusChannel):
                self._logger.error(
                    'Status channel for guild %d is not Messageable',
                    guild_id
                )
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
            self._scrobbler_logger.setLevel(INFO)

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
                session_id = self.database.get_session_id(node.id)
            except OperationalError:
                session_id = None
                self._logger.debug('No session ID for node `%s\'', node.id)
            else:
                self._logger.debug(
                    'Using session ID `%s\' for node `%s\'',
                    session_id,
                    node.id
                )

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
        """
        Send a now playing message for the specified track start event.
        """
        guild_id = event.player.guild.id
        channel = self.get_status_channel(guild_id)
        if channel is None:
            raise ValueError(f'Status channel has not been set for guild {guild_id}')

        # Delete last now playing message, if it exists
        last_msg_id = self.database.get_now_playing(guild_id)
        if last_msg_id != -1:
            try:
                last_msg = await channel.fetch_message(last_msg_id)
                await last_msg.delete()
            except (Forbidden, HTTPException, NotFound):
                pass

        # Send now playing embed
        current_track = event.player.queue[event.player.current_index]
        embed = event.player.now_playing(event.track)
        view = NowPlayingView(self, event.player, current_track.spotify_id)
        msg = await channel.send(embed=embed, view=view)

        # Save now playing message ID
        self.database.set_now_playing(guild_id, msg.id)
