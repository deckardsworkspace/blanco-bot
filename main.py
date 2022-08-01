from nextcord import Activity, ActivityType, Intents, Interaction
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

    # Change presence
    if config['bot']['debug']['enabled']:
        await client.change_presence(activity=Activity(name='/play (debug)', type=ActivityType.listening))
    else:
        await client.change_presence(activity=Activity(name='/play', type=ActivityType.listening))

@client.event
async def on_application_command_error(itx: Interaction, error: Exception):
    await itx.channel.send(embed=create_error_embed(error))

# Run client
if __name__ == '__main__':
    print('Starting bot...')
    client.run(config['bot']['discord_token'])
