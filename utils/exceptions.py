"""
Custom exceptions for Blanco
"""

from typing import Optional, Union


class BlancoException(Exception):
  """
  Custom exception class for Blanco.

  Args:
    - ephemeral (bool): Whether the error message should be ephemeral.
  """

  def __init__(self, message: Union[str, Exception], ephemeral: bool = False):
    self.ephemeral = ephemeral

    if isinstance(message, Exception):
      self.message = str(message)
    else:
      self.message = message

    super().__init__(self.message)

  def __str__(self) -> str:
    return self.message


class EmptyQueueError(BlancoException):
  """
  Raised when the queue is empty.
  """

  def __init__(self):
    self.message = 'The queue is empty.'
    super().__init__(self.message)


class EndOfQueueError(BlancoException):
  """
  Raised when the end of the queue is reached.
  """

  def __init__(self, message: Optional[str] = None):
    self.message = message or 'End of queue reached.'
    super().__init__(self.message)


class JockeyError(BlancoException):
  """
  Raised when an error warrants disconnection from the voice channel.
  """


class JockeyException(BlancoException):
  """
  Raised when an error does not warrant disconnection from the voice channel.
  """


class LavalinkInvalidIdentifierError(BlancoException):
  """
  Raised when an invalid identifier is passed to Lavalink.
  """

  def __init__(self, url, reason=None):
    self.message = f'Error encountered while processing "{url}": `{reason}`'
    super().__init__(self.message)


class LavalinkSearchError(BlancoException):
  """
  Raised when Lavalink fails to search for a query.
  """

  def __init__(self, query, reason=None):
    self.message = f'Could not search for "{query}" on YouTube. Reason: {reason}'
    super().__init__(self.message)


class SpotifyInvalidURLError(BlancoException):
  """
  Raised when an invalid Spotify link or URI is passed.
  """

  def __init__(self, url):
    self.message = f'Invalid Spotify link or URI: {url}'
    super().__init__(self.message)


class SpotifyNoResultsError(BlancoException):
  """
  Raised when no results are found for a Spotify query.
  """


class VoiceCommandError(BlancoException):
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