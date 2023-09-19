"""
Constants used for API requests.
"""

from yarl import URL

RELEASE = '0.0.0-unknown' # This is replaced by the release tag during CI/CD

USER_AGENT = f'blanco-bot/{RELEASE} ( https://blanco.dantis.me )'

DISCORD_API_BASE_URL = URL.build(
    scheme='https',
    host='discord.com',
    path='/api/v10'
)

LASTFM_API_BASE_URL = URL.build(
    scheme='https',
    host='ws.audioscrobbler.com',
    path='/2.0'
)

MUSICBRAINZ_API_BASE_URL = URL.build(
    scheme='https',
    host='musicbrainz.org',
    path='/ws/2'
)

SPOTIFY_ACCOUNTS_BASE_URL = URL.build(
    scheme='https',
    host='accounts.spotify.com',
    path='/api'
)

SPOTIFY_API_BASE_URL = URL.build(
    scheme='https',
    host='api.spotify.com',
    path='/v1'
)

# A top search result below this threshold will not be considered for playback
# and Blanco will fall back to YouTube search. See
# jockey_helpers.py:check_similarity_weighted() for the computation.
CONFIDENCE_THRESHOLD = 55

SPOTIFY_403_ERR_MSG = ''.join([
    '**Error 403** encountered while trying to {}.\n',
    'This is likely because this instance of Blanco uses Spotify API credentials ',
    'that are in **development mode.** ',
    'See [this page](https://github.com/jareddantis-bots/blanco-bot/wiki/Prerequisites#a-note-on-development-mode) ', # pylint: disable=line-too-long
    'for more information.'
])
