from nextcord import DiscordException, Intents, Message
from nextcord.ext.commands import Bot, Context
from os import environ


# Create bot instance
intents = Intents.default()
intents.message_content = True
client = Bot(command_prefix=environ['DISCORD_BOT_PREFIX'], intents=intents)

# Event listeners
@client.event
async def on_ready():
    print('Logged in as {0}!'.format(client.user))
    client.load_extension('cogs')

@client.event
async def on_message(message: Message):
    # Ignore messages from self
    if message.author == client.user:
        return

    try:
        await client.process_commands(message)
    except Exception as e:
        await message.reply(f'Error while processing command: {e}')

@client.event
async def on_command_error(_: Context, error: DiscordException):
    print(error)

# Run client
if __name__ == '__main__':
    print('Starting bot with prefix: {0}'.format(environ['DISCORD_BOT_PREFIX']))
    client.run(environ['DISCORD_BOT_TOKEN'])