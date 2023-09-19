"""
Utilities for fuzzy string matching.
"""

from difflib import get_close_matches

from thefuzz import fuzz


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
        (naive * 0.7) +
        (tsr * 0.12) +
        (candidate_rank * 0.08) +
        (tsor * 0.06) +
        (ptsr * 0.04)
    )
