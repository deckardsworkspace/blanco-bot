from time import time
from typing import TYPE_CHECKING

from nextcord import VoiceChannel

from bot.utils.exceptions import BlancoException
from bot.utils.musicbrainz import annotate_track

if TYPE_CHECKING:
  from nextcord.abc import Connectable

  from bot.models.queue_item import QueueItem
  from bot.utils.blanco import BlancoBot


_SEC_IN_MSEC = 1000
_MIN_IN_SEC = 60
MIN_TRACK_LENGTH_MSEC = 30 * _SEC_IN_MSEC
MIN_ELAPSED_MSEC = 4 * _MIN_IN_SEC * _SEC_IN_MSEC


class ScrobbleHandler:
  """
  Scrobbler class for scrobbling tracks to Last.fm.
  """

  def __init__(self, bot: 'BlancoBot', channel: 'Connectable'):
    self._bot = bot
    self._channel = channel

  def scrobble(self, track: 'QueueItem'):
    try:
      self._validate_config()
      length = self._validate_track_length(track)
      self._validate_elapsed(track, length)
      self._ensure_annotations(track)

      self._scrobble_for_humans(track)
    except AssertionError as e:
      raise BlancoException(f"Cannot scrobble `{track.title}': {e}")

  def _validate_config(self):
    assert self._bot.config is not None, 'Config is not loaded.'
    if not self._bot.config.lastfm_enabled:
      raise BlancoException('Last.fm is not enabled.')

  def _validate_track_length(self, track: 'QueueItem') -> int:
    """
    Validate the length of the track to be scrobbled.

    Args:
      track (QueueItem): The track to be scrobbled.

    Returns:
      int: The length of the track in milliseconds.
    """
    length = track.duration
    if track.lavalink_track is not None:
      length = track.lavalink_track.length

    assert length is not None, 'Cannot scrobble track with no duration.'
    assert length >= MIN_TRACK_LENGTH_MSEC, 'Track is too short to scrobble.'
    return length

  def _validate_elapsed(self, track: 'QueueItem', duration: int):
    now = int(time())
    start_time = track.start_time or now
    elapsed_ms = (now - start_time) * _SEC_IN_MSEC
    assert elapsed_ms >= min(
      duration // 2, MIN_ELAPSED_MSEC
    ), 'Not enough time elapsed.'

  def _ensure_annotations(self, track: 'QueueItem'):
    annotate_track(track)

    has_mbid = track.mbid is not None
    has_isrc = track.isrc is not None
    assert has_mbid or has_isrc, 'No MusicBrainz ID or ISRC found.'

  def _scrobble_for_humans(self, track: 'QueueItem'):
    assert isinstance(self._channel, VoiceChannel), 'Not in a voice channel.'

    human_members = [m for m in self._channel.members if not m.bot]
    assert len(human_members) > 0, 'No human members in the voice channel.'

    for human in human_members:
      scrobbler = self._bot.get_scrobbler(human.id)
      if scrobbler is not None:
        scrobbler.scrobble(track)
