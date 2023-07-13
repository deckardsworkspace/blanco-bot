from nextcord import Intents
from utils.config import config
from utils.lavalink_bot import LavalinkBot


# Create bot instance
intents = Intents.default()
intents.members = True
client = LavalinkBot(intents=intents)
client.init_config(config)


# Run client
if __name__ == '__main__':
    print('Starting bot...')
    if not client.debug:
        client._bot_loop.start()
    client.run(config['bot']['discord_token'])
