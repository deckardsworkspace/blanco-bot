from collections import deque
from dataclass.custom_embed import CustomEmbed
from lavalink.events import *
from lavalink.models import DefaultPlayer
from nextcord import Interaction
from nextcord.abc import Messageable
from .database import Database
from .jockey_helpers import *
from .lavalink import LavalinkVoiceClient
from .lavalink_bot import LavalinkBot
from .lavalink_helpers import EventWithPlayer, lavalink_enqueue
from .spotify_client import Spotify


class Jockey:
    """
    Class that handles music playback for a single guild.
    Contains all the methods for music playback, along with a
    local instance of an in-memory database for fast queueing.
    """

    def __init__(self, guild: int, db: Database, bot: LavalinkBot, player: DefaultPlayer, spotify: Spotify, channel: Messageable):
        self._bot = bot
        self._guild = guild
        self._spotify = spotify
        self._channel = channel

        # Database
        self._db = db
        self._db.init_guild(guild)

        # Player instance
        self._player = player
        manual_await(player.set_volume(db.get_volume(guild)))
        player.set_repeat(db.get_loop(guild))

        # Queue
        self._queue = deque()
        self._current = -1

        # Shuffle indices
        self._shuffled = db.get_shuffle(guild)
        self._shuffle_indices = []

        print(f'Created jockey for guild {guild}')
    
    @property
    def is_connected(self) -> bool:
        return self._player.is_connected
    
    @property
    def is_playing(self) -> bool:
        return self._player is not None and (self._player.is_playing or self._player.paused)

    async def destroy(self):
        # Disconnect Lavalink
        await self._player.stop()
        await self._bot.lavalink.player_manager.destroy(self._guild)
    
    async def handle_event(self, event: EventWithPlayer):
        """
        Handle an event from the Lavalink player.
        """
        if isinstance(event, TrackStartEvent):
            # Send now playing embed
            current_item = self._queue[self._current]
            embed = create_now_playing_embed(current_item)
            await self._channel.send(embed=embed)
        elif isinstance(event, QueueEndEvent):
            # Play next track in queue
            await self.skip(queue_end=True)
    
    async def play(self, itx: Interaction, query: str):
        # Get results for query
        new_tracks = await parse_query(itx, self._spotify, query)
        if len(new_tracks):
            # Connect to voice
            if not self.is_connected:
                # Are we connected according to Discord?
                for client in self._bot.voice_clients:
                    if client.guild.id == self._guild:
                        # Remove old connection
                        await client.disconnect()
                await itx.user.voice.channel.connect(cls=LavalinkVoiceClient)

            # Add new tracks to queue
            old_size = len(self._queue)
            self._queue.extend(new_tracks)

            # Are we beginning a new queue?
            first = new_tracks[0]
            first_name = f'**{first.title}**\nby {first.artist}' if first.title is not None else query
            if not self.is_playing:
                # We are! Play the first track.
                self._current = 0
                if not await lavalink_enqueue(self._player, new_tracks[0]):
                    # Failed to enqueue
                    self._queue.clear()
                    self._current = -1
                    return await itx.followup.send(embed=create_error_embed(f'Failed to enqueue {first_name}'))
            else:
                # We are already playing from a queue.
                # Update shuffle indices if applicable.
                if len(self._shuffle_indices) > 0:
                    # Append new indices to the end of the list
                    new_indices = [old_size + i for i in range(len(new_tracks))]
                    self._shuffle_indices.extend(new_indices)

            # Send embed
            embed = CustomEmbed(
                color=Color.gold(),
                title=':white_check_mark:｜Added to queue',
                description=first_name if len(new_tracks) == 1 else f'{len(new_tracks)} item(s)'
            )
            await itx.followup.send(embed=embed.get())

    async def skip(self, queue_end: bool = False):
        pass
