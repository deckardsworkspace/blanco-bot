"""
Queue manager class for the player cog.
"""

from random import shuffle
from typing import TYPE_CHECKING, List, Tuple

from bot.dataclass.queue_item import QueueItem
from bot.utils.exceptions import EmptyQueueError, EndOfQueueError
from bot.utils.logger import create_logger

if TYPE_CHECKING:
  from database import Database


class QueueManager:
  """
  Queue manager for Blanco's Jockey.
  """

  def __init__(self, guild_id: int, database: 'Database', /):
    self._guild_id = guild_id
    self._queue: List[QueueItem] = []
    self._shuf_i: List[int] = []

    # Restore loop preferences from database
    self._db = database
    self._loop_one = database.get_loop(guild_id)
    self._loop_all = database.get_loop_all(guild_id)

    # The current track index.
    # Even if the queue is shuffled, this must ALWAYS
    # correspond to an element in self._queue, not self._shuf_i.
    self._i = -1

    # Logger
    self._logger = create_logger(self.__class__.__name__)
    self._logger.info('Initialized queue manager for guild %d', guild_id)

  @property
  def queue(self) -> List[QueueItem]:
    """
    Returns the queue.
    """
    return self._queue

  @property
  def shuffled_queue(self) -> List[QueueItem]:
    """
    Returns the queue, shuffled.
    """
    if not self.is_shuffling:
      return self.queue
    return [self.queue[i] for i in self._shuf_i]

  @property
  def is_shuffling(self) -> bool:
    """
    Returns whether the queue is shuffled.
    """
    return len(self._shuf_i) > 0

  @property
  def is_looping_one(self) -> bool:
    """
    Returns whether the queue is looping the current track.
    """
    return self._loop_one

  @is_looping_one.setter
  def is_looping_one(self, value: bool):
    """
    Sets whether the queue is looping the current track.
    """
    self._loop_one = value
    self._db.set_loop(self._guild_id, value)

  @property
  def is_looping_all(self) -> bool:
    """
    Returns whether the queue is looping all tracks.
    """
    return self._loop_all

  @is_looping_all.setter
  def is_looping_all(self, value: bool):
    """
    Sets whether the queue is looping all tracks.
    """
    self._loop_all = value
    self._db.set_loop_all(self._guild_id, value)

  @property
  def size(self) -> int:
    """
    Returns the size of the queue.
    """
    return len(self.queue)

  @property
  def current(self) -> QueueItem:
    """
    Returns the current track in the queue.

    Raises:
        EmptyQueueError: If the queue is empty.
    """
    if self.size == 0:
      raise EmptyQueueError

    return self.queue[self.current_index]

  @property
  def current_index(self) -> int:
    """
    Returns the current track index, NOT accounting for shuffling.
    This is the index of the current track in self._queue.
    """
    return self._i

  @current_index.setter
  def current_index(self, i: int):
    """
    Sets the current track index.

    Args:
        i: The new current track index. Must be adjusted for shuffling,
            i.e., i must correspond to an element in self._queue,
            not self._shuf_i.
    """
    self._i = i

  @property
  def current_shuffled_index(self) -> int:
    """
    Returns the current track index, accounting for shuffling.
    This is the index of the current track in self._shuf_i.
    """
    if not self.is_shuffling:
      return self.current_index
    return self._shuf_i.index(self.current_index)

  @property
  def next_track(self) -> Tuple[int, QueueItem]:
    """
    Returns a tuple containing the index of the next track in the queue
    and the track itself.

    Raises:
        EmptyQueueError: If the queue is empty.
        EndOfQueueError: If the last track in the queue is reached.
    """
    if self.size == 0:
      raise EmptyQueueError

    try:
      i = self.calc_next_index()
      track = self.queue[i]
    except EndOfQueueError as err:
      raise EndOfQueueError('No next track in queue.') from err

    return i, track

  @property
  def previous_track(self) -> Tuple[int, QueueItem]:
    """
    Returns a tuple containing the index of the previous track in the queue
    and the track itself.

    Raises:
        EmptyQueueError: If the queue is empty.
        EndOfQueueError: If the first track in the queue is reached.
    """
    if self.size == 0:
      raise EmptyQueueError

    try:
      i = self.calc_next_index(delta=-1)
      track = self.queue[i]
    except EndOfQueueError as err:
      raise EndOfQueueError('No previous track in queue.') from err

    return i, track

  def calc_next_index(self, *, delta: int = 1) -> int:
    """
    Calculate the next track index, accounting for shuffling and
    looping a single track.

    Args:
        delta: How far ahead or back to seek the next index.

    Returns:
        The next track index in self._queue.

    Raises:
        EndOfQueueError: If one of the ends of the queue is reached,
            and the queue is not looping all tracks.
    """
    forward = delta > 0

    # Return the current index if the queue is looping a single track.
    next_i = self.current_index
    if self.is_looping_one:
      return next_i

    # If we're shuffling, we need to use self._shuf_i to calculate the next index.
    # Otherwise, we can just use the current index.
    if self.is_shuffling:
      next_i = self._shuf_i.index(next_i)

    # Calculate the next index.
    next_i += delta
    if (next_i >= self.size and forward) or (next_i < 0 and not forward):
      if self.is_looping_all:
        next_i = 0 if forward else self.size - 1
      else:
        raise EndOfQueueError

    # If we're shuffling, we need to convert the next index back to
    # an index in self._queue.
    if self.is_shuffling:
      next_i = self._shuf_i[next_i]
    return next_i

  def skip(self) -> QueueItem:
    """
    Returns the next track in the queue and adjusts the current
    track index.

    Raises:
        EmptyQueueError: If the queue is empty.
        EndOfQueueError: If the last track in the queue is reached.
    """
    i, track = self.next_track
    self._i = i
    return track

  def rewind(self) -> QueueItem:
    """
    Returns the previous track in the queue and adjusts the current
    track index.

    Raises:
        EmptyQueueError: If the queue is empty.
        EndOfQueueError: If the first track in the queue is reached.
    """
    i, track = self.previous_track
    self._i = i
    return track

  def shuffle(self):
    """
    Shuffles the queue non-destructively by generating a random
    permutation of indices. Each call to shuffle() will generate
    a different permutation, with the current track always at
    the beginning.

    Raises:
        EmptyQueueError: If the queue is empty.
    """
    if self.size == 0:
      raise EmptyQueueError

    # Shuffle everything except the current track.
    indices = [i for i in range(self.size) if i != self.current_index]
    shuffle(indices)

    # Prepend the current track index to the shuffle index list.
    self._shuf_i = [self.current_index] + indices

  def unshuffle(self):
    """
    Unshuffles the queue by clearing the shuffle index list.
    """
    self._shuf_i = []

  def extend(self, items: List[QueueItem]):
    """
    Appends multiple items to the end of the queue.

    Args:
        items: The QueueItems to append.
    """
    new_queue = self.size == 0

    # Append the items to the queue.
    self.queue.extend(items)
    if self.is_shuffling:
      self._shuf_i.extend(list(range(self.size - len(items), self.size)))

    # Update index
    if new_queue:
      self.current_index = 0

  def insert(self, item: QueueItem, /, index: int):
    """
    Inserts an item in the queue at a specified index.

    Args:
        item: The QueueItem to insert.
        index: The index at which to insert the item.

    Raises:
        EmptyQueueError: If the queue is empty and we are trying
            to insert past index zero. Use enqueue() instead.
        IndexError: If the index is out of range.
    """
    if self.size == 0 and index != 0:
      raise EmptyQueueError
    if not 0 <= index <= self.size:
      raise IndexError(f'Index {index} out of range.')

    if self.is_shuffling:
      # If we're shuffling, insert the item at the end of self._queue,
      # then insert the new index at the specified index in self._shuf_i.
      self.queue.append(item)
      self._shuf_i.insert(index, self.size - 1)
    else:
      # Otherwise, just insert the item at the specified index in self._queue.
      self.queue.insert(index, item)

  def move(self, source_i: int, dest_i: int, /):
    """
    Moves a queue item from one index to another.

    Args:
        source_i: The index of the item to move.
        dest_i: The index to move the item to.

    Raises:
        EmptyQueueError: If the queue is empty.
        IndexError: If either index is out of range, or if the
            source and destination indices are the same, or if
            the source index is the current track index.
    """
    if self.size == 0:
      raise EmptyQueueError
    if not 0 <= source_i < self.size:
      raise IndexError(f'Source index {source_i} out of range.')
    if not 0 <= dest_i < self.size:
      raise IndexError(f'Destination index {dest_i} out of range.')
    if source_i == dest_i:
      raise IndexError('Source and destination indices are the same.')
    if source_i == self.current_index:
      raise IndexError('Cannot move the current track.')

    self.insert(self.remove(source_i), dest_i)

  def remove(self, index: int, /) -> QueueItem:
    """
    Removes an element at the given index and returns the element.

    Raises:
        EmptyQueueError: If the queue is empty.
        IndexError: If the index is out of range.
    """
    if self.size == 0:
      raise EmptyQueueError
    if not 0 <= index < self.size:
      raise IndexError(f'Index {index} out of range.')

    # Adjust the index if we're shuffling.
    adjusted_index = index
    if self.is_shuffling:
      # Remove the index from self._shuf_i.
      adjusted_index = self._shuf_i.pop(index)

      # Adjust the indices in self._shuf_i.
      for i, j in enumerate(self._shuf_i):
        if j > index:
          self._shuf_i[i] -= 1

    # If we're removing the current track, adjust the current track index.
    if adjusted_index == self.current_index:
      self._i = self.calc_next_index()

    # Remove the element from self._queue.
    return self.queue.pop(adjusted_index)
