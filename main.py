from nextcord import Intents
from os import environ
from utils.lavalink_bot import LavalinkBot


# Create bot instance
client = LavalinkBot(intents=Intents.none())

# Event listeners
@client.event
async def on_ready():
    print('Logged in as {0}!'.format(client.user))
    client.load_extension('cogs')

# Run client
if __name__ == '__main__':
    print('Starting bot...')
    client.run(environ['DISCORD_BOT_TOKEN'])
