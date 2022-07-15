from nextcord.abc import Messageable
from .constants import LOOP_DISABLED, LOOP_SINGLE, LOOP_ALL
from .database import Database


class Jockey:
    """
    Class that handles music playback for a single guild.
    Contains all the methods for music playback, along with a
    local instance of an in-memory database for fast queueing.
    """

    def __init__(self, guild: int, db: Database, channel: Messageable):
        self._guild = guild
        self._channel = channel

        # Database
        self._db = db
        self._db.init_guild(guild)

        # Queue
        self._queue = []

        # Shuffle indices
        self._shuffled = db.get_shuffle(guild)
        self._shuffle_indices = []

        # Queue looping
        self._loop = db.get_loop(guild)

        # Volume
        self._volume = db.get_volume(guild)
