from nextcord import Intents, Interaction
from utils.config import config
from utils.jockey_helpers import create_error_embed
from utils.lavalink_bot import LavalinkBot

# Create bot instance
client = LavalinkBot(intents=Intents.default(), config=config)


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
    client._begin_presence()
    client.run(config['bot']['discord_token'])
