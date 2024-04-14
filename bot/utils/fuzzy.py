"""
Utilities for fuzzy string matching.
"""

from difflib import get_close_matches
from typing import List, Tuple, TypeVar

from mafic import SearchType
from thefuzz import fuzz

from .logger import create_logger

LOGGER = create_logger('fuzzy')
T = TypeVar('T')


def check_similarity(actual: str, candidate: str) -> float:
  """
  Checks the similarity between two strings. Meant for comparing
  song titles and artists with search results.

  :param actual: The actual string.
  :param candidate: The candidate string, i.e. from a search result.
  :return: A float from 0 to 1, where 1 is a perfect match.
  """
  actual_words = set(actual.lower().split(' '))
  candidate_words = set(candidate.lower().split(' '))
  intersection = actual_words.intersection(candidate_words)
  difference = actual_words.difference(candidate_words)

  # Get words not in intersection
  for word in difference:
    # Look for close matches
    close_matches = get_close_matches(word, candidate_words, cutoff=0.9)
    if len(close_matches) > 0:
      intersection.add(close_matches[0])

  return len(intersection) / len(actual_words)


def check_similarity_weighted(actual: str, candidate: str, candidate_rank: int) -> int:
  """
  Checks the similarity between two strings using a weighted average
  of a given similarity score and the results of multiple fuzzy string
  matching algorithms. Meant for refining search results that are
  already ranked.

  :param actual: The actual string.
  :param candidate: The candidate string, i.e. from a search result.
  :param candidate_rank: The rank of the candidate, from 0 to 100.
  :return: An integer from 0 to 100, where 100 is the closest match.
  """
  naive = check_similarity(actual, candidate) * 100
  tsr = fuzz.token_set_ratio(actual, candidate)
  tsor = fuzz.token_sort_ratio(actual, candidate)
  ptsr = fuzz.partial_token_sort_ratio(actual, candidate)

  return int(
    (naive * 0.7)
    + (tsr * 0.12)
    + (candidate_rank * 0.08)
    + (tsor * 0.06)
    + (ptsr * 0.04)
  )


def rank_results(
  query: str, results: List[T], result_type: SearchType
) -> List[Tuple[T, int]]:
  """
  Ranks search results based on similarity to a fuzzy query.

  :param query: The query to check against.
  :param results: The results to rank. Can be mafic.Track, dataclass.SpotifyTrack,
      or any object with a title and author string attribute.
  :param result_type: The type of result. See ResultType.
  :return: A list of tuples containing the result and its similarity to the query.
  """
  # Rank results
  similarities = [
    check_similarity_weighted(
      query,
      f'{result.title} {result.author}',  # type: ignore
      int(100 * (0.8**i)),
    )
    for i, result in enumerate(results)
  ]
  ranked = sorted(zip(results, similarities), key=lambda x: x[1], reverse=True)

  # Print confidences for debugging
  type_name = 'YouTube'
  if result_type == SearchType.SPOTIFY_SEARCH:
    type_name = 'Spotify'
  elif result_type == SearchType.DEEZER_SEARCH:
    type_name = 'Deezer'
  LOGGER.debug('%s results and confidences for "%s":', type_name, query)
  for result, confidence in ranked:
    LOGGER.debug(
      '  %3d  %-20s  %-25s',
      confidence,
      result.author[:20],  # type: ignore
      result.title[:25],  # type: ignore
    )

  return ranked
