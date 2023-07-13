from mafic import TrackStartEvent, TrackEndEvent
from nextcord import Activity, ActivityType, Intents, Interaction, PartialMessageable
from typing import TYPE_CHECKING
from utils.config import config
from utils.jockey_helpers import create_error_embed
from utils.lavalink_bot import LavalinkBot
if TYPE_CHECKING:
    from utils.jockey import Jockey

# Create bot instance
intents = Intents.default()
intents.members = True
client = LavalinkBot(intents=intents)
client.init_config(config)


# Event listeners
@client.event
async def on_ready():
    print('Logged in as {0}!'.format(client.user))
    client.load_extension('cogs')
    if client.debug:
        print('Debug mode enabled!')
        await client.change_presence(activity=Activity(name='/play (debug)', type=ActivityType.listening))


@client.event
async def on_application_command_error(itx: Interaction, error: Exception):
    if isinstance(itx.channel, PartialMessageable):
        await itx.channel.send(embed=create_error_embed(str(error)))


# Lavalink-specific event listeners
@client.event
async def on_track_start(event: TrackStartEvent['Jockey']):
    # Send now playing embed
    await client.send_now_playing(event)


@client.event
async def on_track_end(event: TrackEndEvent['Jockey']):
    # Play next track in queue
    await event.player.skip()


# Run client
if __name__ == '__main__':
    print('Starting bot...')
    if not client.debug:
        client._bot_loop.start()
    client.run(config['bot']['discord_token'])
