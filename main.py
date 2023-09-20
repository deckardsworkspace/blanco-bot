"""
Main bot file.
"""

from nextcord import Intents

from utils.blanco import BlancoBot
from utils.config import (REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, SENTRY_DSN,
                          SENTRY_ENV, config)
from utils.constants import RELEASE
from utils.logger import create_logger


if __name__ == '__main__':
    logger = create_logger('main')

    # Print parsed config
    if config.debug_enabled:
        logger.debug('Parsed configuration:')
        logger.debug('  Database file: %s', config.db_file)
        logger.debug('  Discord token: %s...', config.discord_token[:3])
        logger.debug('  Spotify client ID: %s...', config.spotify_client_id[:3])
        logger.debug('  Spotify client secret: %s...', config.spotify_client_secret[:3])
        logger.debug('  Match ahead: %s', 'enabled' if config.match_ahead else 'disabled')

        if SENTRY_DSN is not None and SENTRY_ENV is not None:
            logger.debug('  Sentry DSN: %s...', SENTRY_DSN[:10])
            logger.debug('  Sentry environment: %s', SENTRY_ENV)
        else:
            logger.debug('  Sentry integration disabled')

        if REDIS_HOST is not None and REDIS_PORT != -1:
            logger.debug('  Redis host: %s', REDIS_HOST)
            logger.debug('  Redis port: %d', REDIS_PORT)
            if REDIS_PASSWORD is not None:
                logger.debug('  Redis password: %s...', REDIS_PASSWORD[:3])
        else:
            logger.debug('  Redis integration disabled')

        if config.lastfm_enabled:
            assert config.lastfm_api_key is not None and config.lastfm_shared_secret is not None
            logger.debug('  Last.fm API key: %s...', config.lastfm_api_key[:3])
            logger.debug('  Last.fm shared secret: %s...', config.lastfm_shared_secret[:3])
        else:
            logger.debug('  Last.fm integration disabled')

        logger.debug('  Webserver: %s', 'enabled' if config.enable_server else 'disabled')
        if config.enable_server:
            assert config.discord_oauth_secret is not None
            logger.debug('    - Listening on port %d', config.server_port)
            logger.debug('    - Base URL: %s', config.base_url)
            logger.debug('    - OAuth ID: %s...', str(config.discord_oauth_id)[:3])
            logger.debug('    - OAuth secret: %s...', config.discord_oauth_secret[:3])

        logger.debug('  Lavalink nodes:')
        for node in config.lavalink_nodes.values():
            logger.debug('    - %s (%s:%d)', node.id, node.host, node.port)
            logger.debug('      Secure: %s', 'yes' if node.secure else 'no')
            logger.debug('      Supports Deezer: %s', 'yes' if node.deezer else 'no')
            logger.debug('      Regions: %s', ', '.join(node.regions))

    # Create bot instance
    intents = Intents.default()
    intents.members = True
    client = BlancoBot(intents=intents, default_guild_ids=config.debug_guild_ids)
    client.init_config(config)

    # Run client
    logger.info('Blanco release %s booting up...', RELEASE)
    client.run(config.discord_token)
