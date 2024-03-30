"""
Custom exceptions for Blanco
"""


class EmptyQueueError(Exception):
  """
  Raised when the queue is empty.
  """

  def __init__(self):
    self.message = 'The queue is empty.'
    super().__init__(self.message)


class EndOfQueueError(Exception):
  """
  Raised when the end of the queue is reached.
  """


class JockeyError(Exception):
  """
  Raised when an error warrants disconnection from the voice channel.
  """


class JockeyException(Exception):
  """
  Raised when an error does not warrant disconnection from the voice channel.
  """


class LavalinkInvalidIdentifierError(Exception):
  """
  Raised when an invalid identifier is passed to Lavalink.
  """

  def __init__(self, url, reason=None):
    self.message = f'Error encountered while processing "{url}": `{reason}`'
    super().__init__(self.message)


class LavalinkSearchError(Exception):
  """
  Raised when Lavalink fails to search for a query.
  """

  def __init__(self, query, reason=None):
    self.message = f'Could not search for "{query}" on YouTube. Reason: {reason}'
    super().__init__(self.message)


class SpotifyInvalidURLError(Exception):
  """
  Raised when an invalid Spotify link or URI is passed.
  """

  def __init__(self, url):
    self.message = f'Invalid Spotify link or URI: {url}'
    super().__init__(self.message)


class SpotifyNoResultsError(Exception):
  """
  Raised when no results are found for a Spotify query.
  """


class VoiceCommandError(Exception):
  """
  Raised when a command that requires a voice channel is invoked outside of one.
  """

class BumpError(Exception):
  """
  Raised when encountering an error while playing a bump.
  """

class BumpNotReadyError(Exception):
  """
  Raised when it hasn't been long enough between bumps.
  """

class BumpNotEnabledError(Exception):
  """
  Raised when bumps are not enabled in a guild.
  """