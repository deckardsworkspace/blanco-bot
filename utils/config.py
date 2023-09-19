"""
Configuration parser.

This module parses the configuration file and environment variables and
provides a single object with the synthesized configuration values,
where the environment variables take precedence over the config file.
"""

from os import environ
from os.path import isfile
from typing import Dict

from yaml import safe_load

from dataclass.config import Config, LavalinkNode


DATABASE_FILE = None
DISCORD_TOKEN = None
SPOTIFY_CLIENT_ID = None
SPOTIFY_CLIENT_SECRET = None
ENABLE_SERVER = False
SERVER_PORT = 8080
SERVER_BASE_URL = None
DISCORD_OAUTH_ID = None
DISCORD_OAUTH_SECRET = None
LASTFM_API_KEY = None
LASTFM_SHARED_SECRET = None
LAVALINK_NODES: Dict[str, LavalinkNode] = {}
SENTRY_DSN = None
SENTRY_ENV = None
DEBUG_ENABLED = False
DEBUG_GUILDS = None

# Parse config file if it exists
if isfile('config.yml'):
    with open('config.yml', encoding='UTF-8') as f:
        try:
            config_file = safe_load(f)
        except Exception as e:
            raise ValueError(f'Error parsing config.yml: {e}') from e

        # Get config values
        try:
            # Read config from config.yml
            DATABASE_FILE = config_file['bot']['database']
            DISCORD_TOKEN = config_file['bot']['discord_token']
            SPOTIFY_CLIENT_ID = config_file['spotify']['client_id']
            SPOTIFY_CLIENT_SECRET = config_file['spotify']['client_secret']

            # Parse Lavalink nodes from config.yml
            for node in config_file['lavalink']:
                lavalink_node = LavalinkNode(
                    id=node['id'],
                    password=node['password'],
                    host=node['server'],
                    port=node['port'],
                    regions=node['regions'],
                    secure=node.get('secure', False)
                )

                # Add optional config values
                if 'deezer' in node:
                    lavalink_node.deezer = node['deezer']

                LAVALINK_NODES[node['id']] = lavalink_node

            # Add optional config values
            if 'server' in config_file:
                ENABLE_SERVER = config_file['server']['enabled']
                SERVER_PORT = config_file['server'].get('port', 8080)
                SERVER_BASE_URL = config_file['server'].get('base_url', None)
                DISCORD_OAUTH_ID = config_file['server'].get('oauth_id', None)
                DISCORD_OAUTH_SECRET = config_file['server'].get('oauth_secret', None)
            if 'lastfm' in config_file:
                LASTFM_API_KEY = config_file['lastfm']['api_key']
                LASTFM_SHARED_SECRET = config_file['lastfm']['shared_secret']
            if 'debug' in config_file['bot']:
                DEBUG_ENABLED = config_file['bot']['debug']['enabled']
                DEBUG_GUILDS = config_file['bot']['debug']['guild_ids']
            if 'sentry' in config_file:
                SENTRY_DSN = config_file['sentry']['dsn']
                SENTRY_ENV = config_file['sentry']['environment']
        except KeyError as e:
            raise RuntimeError(f'Config missing from config.yml: {e.args[0]}') from e


# Override config from environment variables
DATABASE_FILE = environ.get('BLANCO_DB_FILE', DATABASE_FILE)
DISCORD_TOKEN = environ.get('BLANCO_TOKEN', DISCORD_TOKEN)
LASTFM_API_KEY = environ.get('BLANCO_LASTFM_KEY', LASTFM_API_KEY)
LASTFM_SHARED_SECRET = environ.get('BLANCO_LASTFM_SECRET', LASTFM_SHARED_SECRET)
SPOTIFY_CLIENT_ID = environ.get('BLANCO_SPOTIFY_ID', SPOTIFY_CLIENT_ID)
SPOTIFY_CLIENT_SECRET = environ.get('BLANCO_SPOTIFY_SECRET', SPOTIFY_CLIENT_SECRET)
SENTRY_DSN = environ.get('BLANCO_SENTRY_DSN', SENTRY_DSN)
SENTRY_ENV = environ.get('BLANCO_SENTRY_ENV', SENTRY_ENV)
if 'BLANCO_DEBUG' in environ:
    DEBUG_ENABLED = environ['BLANCO_DEBUG'].lower() == 'true'
    DEBUG_GUILDS = [int(id) for id in environ['BLANCO_DEBUG_GUILDS'].split(',')]
if 'BLANCO_ENABLE_SERVER' in environ:
    ENABLE_SERVER = environ['BLANCO_ENABLE_SERVER'].lower() == 'true'
    SERVER_PORT = int(environ.get('BLANCO_SERVER_PORT', SERVER_PORT))
    SERVER_BASE_URL = environ.get('BLANCO_BASE_URL', SERVER_BASE_URL)
    DISCORD_OAUTH_ID = environ.get('BLANCO_OAUTH_ID', DISCORD_OAUTH_ID)
    DISCORD_OAUTH_SECRET = environ.get('BLANCO_OAUTH_SECRET', DISCORD_OAUTH_SECRET)

# Parse Lavalink nodes from environment variables
i = 1
while True:
    try:
        credentials, host = environ[f'BLANCO_NODE_{i}'].split('@')
        node_id, password = credentials.split(':')
        server, port = host.split(':')
        regions = environ[f'BLANCO_NODE_{i}_REGIONS'].split(',')
        secure = environ.get(f'BLANCO_NODE_{i}_SECURE', 'false').lower() == 'true'
        deezer = environ.get(f'BLANCO_NODE_{i}_DEEZER', 'false').lower() == 'true'
    except KeyError as e:
        missing_key = e.args[0]
        if missing_key == f'BLANCO_NODE_{i}':
            if len(LAVALINK_NODES) == 0:
                raise ValueError('No Lavalink nodes specified') from e
            break

        if missing_key == f'BLANCO_NODE_{i}_REGIONS':
            raise ValueError(f'No regions specified for Lavalink node {i}') from e

        break
    else:
        # Add node to list
        LAVALINK_NODES[node_id] = LavalinkNode(
            id=node_id,
            password=password,
            host=server,
            port=int(port),
            regions=regions,
            secure=secure,
            deezer=deezer
        )

        i += 1


# Final checks
if DATABASE_FILE is None:
    raise ValueError('No database file specified')
if DISCORD_TOKEN is None:
    raise ValueError('No Discord token specified')
if SPOTIFY_CLIENT_ID is None:
    raise ValueError('No Spotify client ID specified')
if SPOTIFY_CLIENT_SECRET is None:
    raise ValueError('No Spotify client secret specified')
if ENABLE_SERVER and (DISCORD_OAUTH_ID is None or
                      DISCORD_OAUTH_SECRET is None or SERVER_BASE_URL is None):
    raise ValueError('Discord OAuth ID, secret, and base URL must be specified to enable server')


# Create config object
config = Config(
    db_file=DATABASE_FILE,
    discord_token=DISCORD_TOKEN,
    spotify_client_id=SPOTIFY_CLIENT_ID,
    spotify_client_secret=SPOTIFY_CLIENT_SECRET,
    lavalink_nodes=LAVALINK_NODES,
    debug_enabled=DEBUG_ENABLED,
    debug_guild_ids=DEBUG_GUILDS,
    enable_server=ENABLE_SERVER,
    server_port=SERVER_PORT,
    base_url=SERVER_BASE_URL,
    discord_oauth_id=DISCORD_OAUTH_ID,
    discord_oauth_secret=DISCORD_OAUTH_SECRET,
    lastfm_api_key=LASTFM_API_KEY,
    lastfm_shared_secret=LASTFM_SHARED_SECRET
)
