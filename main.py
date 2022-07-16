from nextcord import Intents, Interaction
from os import environ
from utils.jockey_helpers import create_error_embed
from utils.lavalink_bot import LavalinkBot


# Create bot instance
client = LavalinkBot(intents=Intents.default())

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
    client.run(environ['DISCORD_BOT_TOKEN'])
