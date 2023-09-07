"""
Main bot file.
"""

from nextcord import Intents

from utils.blanco import BlancoBot
from utils.config import config
from utils.logger import create_logger

# Create bot instance
intents = Intents.default()
client = BlancoBot(intents=intents, default_guild_ids=config.debug_guild_ids)
client.init_config(config)


# Run client
if __name__ == '__main__':
    logger = create_logger('main', config.debug_enabled)
    logger.info('Starting bot...')
    client.run(config.discord_token)
