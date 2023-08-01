blanco-bot
===

[![GitHub Releases](https://img.shields.io/github/v/release/jareddantis-bots/blanco-bot)](https://github.com/jareddantis-bots/blanco-bot/releases/latest)
[![Docker Image CI](https://github.com/jareddantis/blanco-bot/actions/workflows/build.yml/badge.svg)](https://github.com/jareddantis/blanco-bot/actions/workflows/build.yml)
![Docker Pulls](https://img.shields.io/docker/pulls/jareddantis/blanco-bot)

Blanco is a Discord music bot made with [Nextcord](https://nextcord.dev) that supports pulling music metadata from Spotify. Music playback is handled by the [Mafic](https://github.com/ooliver1/mafic) client for the [Lavalink](https://github.com/lavalink-devs/Lavalink) server.

The bot stores data in a local SQLite database. This database is populated automatically on first run, and the data it will contain include Lavalink session IDs, volume levels, and queue repeat preferences per guild.

- [blanco-bot](#blanco-bot)
- [Deployment](#deployment)
  - [Prerequisites](#prerequisites)
  - [With Docker](#with-docker)
  - [Without Docker](#without-docker)
- [Debugging](#debugging)

# Deployment

**Do not monetize, or attempt to submit for verification, any instance of this bot.** The Lavalink audio server pulls audio data from YouTube, which goes against the [YouTube Terms of Service.](https://www.youtube.com/t/terms) At best, Discord will reject your application for verification, and at worst, your developer account will get banned.

## Prerequisites

You will need a working Lavalink server for your own bot instance to work; there is a list of free servers [here.](https://lavalink.darrennathanael.com/)

You could also choose to run Lavalink along with your bot, but make sure you have enough resources to run both Lavalink and the bot. The absolute minimum is 1GB of RAM, which will be enough for a few guilds, but you will need more as your bot grows.

Before proceeding, make sure that you have a bot token from [Discord,](https://discord.com/developers/applications) and that you have a client ID & secret pair from [Spotify.](https://developer.spotify.com/dashboard)

Create an empty directory and create a file named `config.yml` in it, with the following contents:

```yaml
bot:
  database: blanco.db
  discord_token: <your Discord bot token>
spotify:
  client_id: <your client id>
  client_secret: <your client secret>
lavalink:
  - id: main
    server: localhost
    port: 2333
    password: youshallnotpass
    regions: 
      - us-central
      - us-east

    # Set to true if node supports SSL (https://, wss://)
    ssl: false                   
# You may add more than one node here
# - id: backup
#   ...
```

Edit the values with your Discord and Spotify tokens, along with the details of your chosen Lavalink server(s).

We also need to create an empty database file in the same folder, which will be used by the bot to store settings. Open a terminal in the same folder as `config.yml` and run the following command:

```
# Windows cmd
type nul > blanco.db

# Linux, macOS, etc.
touch blanco.db
```

## With Docker

Blanco comes in a Docker image, so you do not have to install anything aside from Docker. All of the dependencies are included in the Docker image, which has been tested on Linux hosts using Docker CE, and on Windows and macOS hosts using Docker Desktop.

Aside from `linux/amd64`, the bot image is built with both `linux/arm/v7` and `linux/arm64` support, so you can, for instance, run the bot on a Raspberry Pi or a Mac with Apple silicon with reasonable performance.

Make sure you followed [Prerequisites](#prerequisites), then create a `docker-compose.yml` file in the same folder with the following contents:

```yaml
version: '3.8'
services:
  blanco-bot:
    image: jareddantis/blanco-bot
    # OR
    # image: ghcr.io/jareddantis-bots/blanco-bot

    container_name: blanco-bot
    volumes:
      - /YOUR/PATH/HERE/config.yml:/opt/app/config.yml
      - /YOUR/PATH/HERE/blanco.db:/opt/app/blanco.db
    restart: unless-stopped
```

Edit `/YOUR/PATH/HERE/config.yml` and `/YOUR/PATH/HERE/blanco.db` to match the paths to your `config.yml` and `blanco.db`.

Finally, in a terminal, run

```bash
docker compose up -d
```

This will cause the bot to run in the background after the container is built. Omit the `-d` if you want it to run in the foreground, printing logs to the terminal as they come. If you get an error regarding the `compose` command or the `docker-compose.yml` file, you might be running an old version of Docker - please update before trying again.

In case there is an update to the bot, just stop the container using

```
docker compose stop
```

then pull the latest bot image using

```
docker compose rm -f
docker compose pull blanco-bot
```

and start the container again using

```bash
docker compose up -d
```

## Without Docker

If you want to deploy Blanco without Docker, make sure you have Python 3.11+ installed. Then:

1. Download the source code ZIP from the latest [release.](https://github.com/jareddantis-bots/blanco-bot/releases/latest)
2. Unpack it into an empty directory.
3. Open a terminal inside that directory and create a virtual environment:
    ```bash
    # Change python3 to whatever your Python 3 binary is called
    python3 -m venv .venv
    ```
4. Activate the virtual environment:
    ```
    # Windows cmd
    .\.venv\Scripts\Activate.bat
    
    # Linux, macOS, etc.
    source .venv/bin/activate
    ```
5. Install Blanco's requirements using `python3 -m pip install -r requirements.txt`.
6. Create `config.yml` and `blanco.db` according to the instructions in [Prerequisites](#prerequisites).
7. Run Blanco using `python3 main.py`.

# Debugging

Blanco has the ability to switch to a debug mode, which is used to
- register slash commands in a specified guild instead of globally like normal, and
- print additional messages to the console, such as the songs played in every guild.

It is not recommended to enable debugging mode outside of testing.

If you would like to enable debugging mode in your own instance, edit the `bot` section in `config.yml` as such, then (re)start your instance:

```yaml
bot:
  # ...
  debug:
    enabled: true
    guild_ids:
      - <your guild id>
      # can add more than 1 guild here
```
