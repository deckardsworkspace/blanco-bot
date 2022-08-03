from nextcord import Activity, ActivityType, Intents, Interaction
from nextcord.ext.tasks import loop
from utils.config import config, get_debug_status
from utils.jockey_helpers import create_error_embed
from utils.lavalink_bot import LavalinkBot

# Create bot instance
client = LavalinkBot(intents=Intents.default(), config=config)


# Event listeners
@client.event
async def on_ready():
    print('Logged in as {0}!'.format(client.user))
    client.load_extension('cogs')

    # Change presence for debug instances
    if get_debug_status():
        await client.change_presence(activity=Activity(name='/play (debug)', type=ActivityType.listening))


@client.event
async def on_application_command_error(itx: Interaction, error: Exception):
    await itx.channel.send(embed=create_error_embed(error))


# Change presence every half hour
show_servers = False
@loop(seconds=1800)
async def bot_loop():
    status = f'{len(client.guilds)} servers | /play' if show_servers else '/play'
    activity = Activity(name=status, type=ActivityType.listening)
    await client.change_presence(activity=activity)
    show_servers = not show_servers

@bot_loop.before_loop
async def bot_loop_before():
    await client.wait_until_ready()


# Run client
if __name__ == '__main__':
    print('Starting bot...')
    client.run(config['bot']['discord_token'])
    if not get_debug_status():
        bot_loop.start()
