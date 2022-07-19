blanco-bot
===

This is a self-contained Discord music bot that supports pulling music metadata from Spotify, made with [Nextcord v2](https://nextcord.dev).

Music playback is handled by the [Lavalink.py](https://github.com/Devoxin/Lavalink.py) client for the [Lavalink](https://github.com/freyacodes/Lavalink) server. A local server is created for you automatically when you start the Docker containers, as detailed in [Deployment](#deployment) below.

The bot stores settings in a local SQLite database. This database is created automatically on first run, and the settings it will contain include the set volume level and queue repeat preferences per guild.

## Before you proceed

**Do not monetize any instance of this bot.** The Lavalink audio server pulls audio data from YouTube, which is fine for personal use, but not for commercial use (see [YouTube Terms of Service](https://www.youtube.com/t/terms) for more information). If you equip your bot with a premium tier or a similar concept, you risk running the same fate as Groovy and Rythm.

# Requirements

This bot is self-contained, in that you do not have to install anything aside from Docker and Docker Compose. All dependencies are automatically installed within their respective Docker containers.

This bot has been tested on

- Windows 11 + Docker Desktop on Ubuntu/WSL2,
- Arch Linux + Docker 20.10.17 & Docker Compose 2.6.1,
- macOS 12 Monterey + Docker Desktop, and
- macOS 13 Ventura Public Beta + Docker Desktop.

The Dockerfiles in the repository inherit from images that have both `linux/amd64` and `linux/arm64` support, so you can for instance run the bot on Apple Silicon with reasonable performance.

# Deployment

In the repository root directory, create an `.env` file with the following content, customizing values as desired:

```bash
# Filename for the bot's SQLite database
DB_FILENAME="blanco.db"

# Discord token for the bot account
# Obtain one from discord.com/developers/applications/
DISCORD_BOT_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Number of seconds Blanco will wait while not playing
# before automatically disconnecting from voice.
# Must be a non-zero positive integer.
INACTIVE_SEC="120"

# Spotify API credentials for the bot
# Obtain a client ID and client secret from developer.spotify.com/dashboard/
SPOTIFY_ID="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SPOTIFY_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

Make sure you have Docker and Docker Compose installed and up-to-date. Depending on your system, Docker Compose may either be installed as `docker-compose` or `docker compose`; if the former complains about the `docker-compose.yml` file being invalid, try using the latter.

Change your working directory to the repository root, and run

```bash
docker-compose up -d
```

This will cause the bot to run in the background after the containers are built. Omit the `-d` if you want it to run in the foreground, printing logs to the terminal as they come.

In case there is an update to the bot, just stop the containers using

```
docker-compose stop
```

and rebuild them using

```bash
docker-compose up -d --build
```

In some cases, such as when there is a change to the bot database schema, you may need to delete the database file and rebuild the containers as above, but I try my best to make future updates handle migrations smoothly.
