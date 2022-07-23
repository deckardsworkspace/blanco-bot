from nextcord import Intents, Interaction
from utils.jockey_helpers import create_error_embed
from utils.lavalink_bot import LavalinkBot
from yaml import safe_load


# Parse config file
with open('config.yml') as f:
    try:
        config = safe_load(f)
    except Exception as e:
        raise ValueError(f'Error parsing config.yml: {e}')

# Create bot instance
client = LavalinkBot(intents=Intents.default())
client.config = config

# Event listeners
@client.event
async def on_ready():
    print('Logged in as {0}!'.format(client.user))
    client.load_extension('cogs')

@client.event
async def on_application_command_error(itx: Interaction, error: Exception):
    await itx.channel.send(embed=create_error_embed(error))

# Run client
if __name__ == '__main__':
    print('Starting bot...')
    client.run(config['bot']['discord_token'])
