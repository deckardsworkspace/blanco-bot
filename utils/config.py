from dataclass.config import Config, LavalinkNode
from os import environ
from os.path import isfile
from typing import Dict, List, Optional
from yaml import safe_load
from .logger import create_logger


logger = create_logger('config', debug=True)
db_file = None
discord_token = None
spotify_client_id = None
spotify_client_secret = None
lavalink_nodes: Dict[str, LavalinkNode] = {}
debug_enabled = False
debug_guild_ids = None

# Parse config file if it exists
if isfile('config.yml'):
    logger.info('Reading config.yml')

    with open('config.yml') as f:
        try:
            config_file = safe_load(f)
        except Exception as e:
            raise ValueError(f'Error parsing config.yml: {e}')

        # Get config values
        try:
            # Read config from env vars first, then config.yml
            db_file = config_file['bot']['database']
            discord_token = config_file['bot']['discord_token']
            spotify_client_id = config_file['spotify']['client_id']
            spotify_client_secret = config_file['spotify']['client_secret']
            
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

                lavalink_nodes[node['id']] = lavalink_node

            # Add optional config values
            if 'debug' in config_file['bot']:
                debug_enabled = config_file['bot']['debug']['enabled']
                debug_guild_ids = config_file['bot']['debug']['guild_ids']
        except KeyError as e:
            raise ValueError(f'Required config missing from both config.yml and env: {e.args[0]}')


# Override config from environment variables
logger.info('Reading config from environment variables')
db_file = environ.get('BLANCO_DB_FILE', db_file)
discord_token = environ.get('BLANCO_TOKEN', discord_token)
spotify_client_id = environ.get('BLANCO_SPOTIFY_ID', spotify_client_id)
spotify_client_secret = environ.get('BLANCO_SPOTIFY_SECRET', spotify_client_secret)
if 'BLANCO_DEBUG' in environ:
    debug_enabled = environ['BLANCO_DEBUG'].lower() == 'true'
    debug_guild_ids = [int(id) for id in environ['BLANCO_DEBUG_GUILDS'].split(',')]

# Parse Lavalink nodes from environment variables
i = 1
while True:
    try:
        credentials, host = environ[f'BLANCO_NODE_{i}'].split('@')
        id, password = credentials.split(':')
        server, port = host.split(':')
        regions = environ[f'BLANCO_NODE_{i}_REGIONS'].split(',')
        secure = environ.get(f'BLANCO_NODE_{i}_SECURE', 'false').lower() == 'true'
        deezer = environ.get(f'BLANCO_NODE_{i}_DEEZER', 'false').lower() == 'true'
    except KeyError as e:
        missing_key = e.args[0]
        if missing_key == f'BLANCO_NODE_{i}':
            if not len(lavalink_nodes):
                raise ValueError('No Lavalink nodes specified')
            break
        elif missing_key == f'BLANCO_NODE_{i}_REGIONS':
            raise ValueError(f'No regions specified for Lavalink node {i}')
        
        break
    else:
        # Add node to list
        lavalink_nodes[id] = LavalinkNode(
            id=id,
            password=password,
            host=server,
            port=int(port),
            regions=regions,
            secure=secure,
            deezer=deezer
        )

        i += 1


# Final checks
if db_file is None:
    raise ValueError('No database file specified')
if discord_token is None:
    raise ValueError('No Discord token specified')
if spotify_client_id is None:
    raise ValueError('No Spotify client ID specified')
if spotify_client_secret is None:
    raise ValueError('No Spotify client secret specified')

# Print parsed config
if debug_enabled:
    logger.debug(f'Parsed configuration:')
    logger.debug(f'  Database file: {db_file}')
    logger.debug(f'  Discord token: {discord_token[:3]}...{discord_token[-3:]}')
    logger.debug(f'  Spotify client ID: {spotify_client_id[:3]}...{spotify_client_id[-3:]}')
    logger.debug(f'  Spotify client secret: {spotify_client_secret[:3]}...{spotify_client_secret[-3:]}')
    logger.debug(f'  Lavalink nodes:')
    for node in lavalink_nodes.values():
        logger.debug(f'    - {node.id} ({node.host}:{node.port})')
        logger.debug(f'      Secure: {node.secure}')
        logger.debug(f'      Supports Deezer: {node.deezer}')
        logger.debug(f'      Regions: {node.regions}')

# Create config object
config = Config(
    db_file=db_file,
    discord_token=discord_token,
    spotify_client_id=spotify_client_id,
    spotify_client_secret=spotify_client_secret,
    lavalink_nodes=lavalink_nodes,
    debug_enabled=debug_enabled,
    debug_guild_ids=debug_guild_ids
)


def get_debug_guilds() -> Optional[List[int]]:
    return config.debug_guild_ids


def get_debug_status() -> bool:
    return config.debug_enabled
