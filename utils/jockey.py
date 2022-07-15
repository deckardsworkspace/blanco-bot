from lavalink.events import *
from lavalink.models import DefaultPlayer
from nextcord.abc import Messageable
from .database import Database
from .lavalink import EventWithPlayer
from .jockey_helpers import *


class Jockey:
    """
    Class that handles music playback for a single guild.
    Contains all the methods for music playback, along with a
    local instance of an in-memory database for fast queueing.
    """

    def __init__(self, guild: int, db: Database, player: DefaultPlayer, channel: Messageable):
        self._guild = guild
        self._channel = channel

        # Player instance
        self._player = player
        player.set_volume(db.get_volume(guild))
        player.set_repeat(db.get_loop(guild))

        # Database
        self._db = db
        self._db.init_guild(guild)

        # Queue
        self._queue = []
        self._current = -1

        # Shuffle indices
        self._shuffled = db.get_shuffle(guild)
        self._shuffle_indices = []
    
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

    async def skip(self, queue_end: bool = False):
        pass
