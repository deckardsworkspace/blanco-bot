"""
Constants used for API requests.
"""

from yarl import URL


USER_AGENT = 'blanco-bot/0.4.0 ( https://blanco.dantis.me )'

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
