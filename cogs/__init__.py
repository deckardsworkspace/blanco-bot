from utils.database import Database
from utils.jockey_helpers import manual_await
from utils.lavalink_bot import LavalinkBot
from .player import PlayerCog


def setup(bot: LavalinkBot):
    # Create Database instance
    db = Database(bot.config['bot']['database'])

    # Add cogs
    bot.add_cog(PlayerCog(bot, db))

    # Sync slash commands
    if bot.debug:
        print('Syncing slash commands...')
        manual_await(bot.sync_application_commands(guild_id=bot.config['bot']['debug']['guild_id']))
        print('Synced slash commands!')
    else:
        manual_await(bot.sync_application_commands())
