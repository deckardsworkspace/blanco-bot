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
enable_server = False
base_url = None
discord_oauth_id = None
discord_oauth_secret = None
lastfm_api_key = None
lastfm_shared_secret = None
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
            # Read config from config.yml
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
            if 'server' in config_file:
                enable_server = config_file['server']['enabled']
                base_url = config_file['server'].get('base_url', None)
                discord_oauth_id = config_file['server'].get('oauth_id', None)
                discord_oauth_secret = config_file['server'].get('oauth_secret', None)
            if 'lastfm' in config_file:
                lastfm_api_key = config_file['lastfm']['api_key']
                lastfm_shared_secret = config_file['lastfm']['shared_secret']
            if 'debug' in config_file['bot']:
                debug_enabled = config_file['bot']['debug']['enabled']
                debug_guild_ids = config_file['bot']['debug']['guild_ids']
        except KeyError as e:
            logger.warning(f'Config missing from config.yml: {e.args[0]}')


# Override config from environment variables
logger.info('Reading config from environment variables')
db_file = environ.get('BLANCO_DB_FILE', db_file)
discord_token = environ.get('BLANCO_TOKEN', discord_token)
lastfm_api_key = environ.get('BLANCO_LASTFM_KEY', lastfm_api_key)
lastfm_shared_secret = environ.get('BLANCO_LASTFM_SECRET', lastfm_shared_secret)
spotify_client_id = environ.get('BLANCO_SPOTIFY_ID', spotify_client_id)
spotify_client_secret = environ.get('BLANCO_SPOTIFY_SECRET', spotify_client_secret)
if 'BLANCO_DEBUG' in environ:
    debug_enabled = environ['BLANCO_DEBUG'].lower() == 'true'
    debug_guild_ids = [int(id) for id in environ['BLANCO_DEBUG_GUILDS'].split(',')]
if 'BLANCO_ENABLE_SERVER' in environ:
    enable_server = environ['BLANCO_ENABLE_SERVER'].lower() == 'true'
    base_url = environ.get('BLANCO_BASE_URL', base_url)
    discord_oauth_id = environ.get('BLANCO_OAUTH_ID', discord_oauth_id)
    discord_oauth_secret = environ.get('BLANCO_OAUTH_SECRET', discord_oauth_secret)

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
if enable_server and (discord_oauth_id is None or discord_oauth_secret is None or base_url is None):
    raise ValueError('Discord OAuth ID, secret, and base URL must be specified to enable server')

# Print parsed config
if debug_enabled:
    logger.debug(f'Parsed configuration:')
    logger.debug(f'  Database file: {db_file}')
    logger.debug(f'  Discord token: {discord_token[:3]}...{discord_token[-3:]}')
    logger.debug(f'  Spotify client ID: {spotify_client_id[:3]}...{spotify_client_id[-3:]}')
    logger.debug(f'  Spotify client secret: {spotify_client_secret[:3]}...{spotify_client_secret[-3:]}')

    if lastfm_api_key is not None and lastfm_shared_secret is not None:
        logger.debug(f'  Last.fm API key: {lastfm_api_key[:3]}...{lastfm_api_key[-3:]}')
        logger.debug(f'  Last.fm shared secret: {lastfm_shared_secret[:3]}...{lastfm_shared_secret[-3:]}')
    else:
        logger.debug(f'  Last.fm integration disabled')
    
    logger.debug(f'  Webserver: {"enabled" if enable_server else "disabled"}')
    if enable_server:
        assert discord_oauth_id is not None
        assert discord_oauth_secret is not None
        logger.debug(f'    - Base URL: {base_url}')
        logger.debug(f'    - OAuth ID: {str(discord_oauth_id)[:3]}...{str(discord_oauth_id)[-3:]}')
        logger.debug(f'    - OAuth secret: {discord_oauth_secret[:3]}...{discord_oauth_secret[-3:]}')
    
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
    debug_guild_ids=debug_guild_ids,
    enable_server=enable_server,
    base_url=base_url,
    discord_oauth_id=discord_oauth_id,
    discord_oauth_secret=discord_oauth_secret,
    lastfm_api_key=lastfm_api_key,
    lastfm_shared_secret=lastfm_shared_secret
)


def get_debug_guilds() -> Optional[List[int]]:
    return config.debug_guild_ids


def get_debug_status() -> bool:
    return config.debug_enabled
