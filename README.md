blanco-bot
===

<img align="right" src="/server/static/images/logo.svg" width=200 alt="Blanco logo">

Blanco is a Discord music bot made with [Nextcord](https://nextcord.dev) that supports pulling music metadata from Spotify. Music playback is handled by the [Mafic](https://github.com/ooliver1/mafic) client for the [Lavalink](https://github.com/lavalink-devs/Lavalink) server.

[![GitHub Releases](https://img.shields.io/github/v/release/jareddantis-bots/blanco-bot)](https://github.com/jareddantis-bots/blanco-bot/releases/latest)
[![Docker Image CI](https://github.com/jareddantis/blanco-bot/actions/workflows/build.yml/badge.svg)](https://github.com/jareddantis/blanco-bot/actions/workflows/build.yml)
![Docker Pulls](https://img.shields.io/docker/pulls/jareddantis/blanco-bot)

The bot stores data in a local SQLite database. This database is populated automatically on first run, and the data it will contain include Lavalink session IDs, volume levels, and queue repeat preferences per guild.

- [blanco-bot](#blanco-bot)
- [Deployment](#deployment)
  - [Prerequisites](#prerequisites)
  - [Configuration](#configuration)
    - [Environment variables](#environment-variables)
    - [YAML file](#yaml-file)
    - [Database file](#database-file)
  - [With Docker](#with-docker)
  - [Without Docker](#without-docker)
- [Debugging mode](#debugging-mode)

# Deployment

> [!Warning]
> **Do not monetize, or attempt to submit for verification, any instance of this bot.** The Lavalink audio server has the ability to pull audio data from YouTube, which goes against the [YouTube Terms of Service,](https://www.youtube.com/t/terms) and optionally Deezer, which goes against the [Deezer Terms of Use.](https://www.deezer.com/legal/cgu)
>
> At best, Discord will reject your application for verification, and at worst, your developer account will get banned.

## Prerequisites

You will need a working Lavalink server for your own bot instance to work; there is a list of free servers [here.](https://lavalink.darrennathanael.com/)

You could also choose to run Lavalink along with your bot, but make sure you have enough resources to run both Lavalink and the bot. The absolute minimum is 1GB of RAM, which will be enough for a few guilds, but you will need more as your bot grows.

Before proceeding, make sure that you have a bot token from [Discord,](https://discord.com/developers/applications) and that you have a client ID & secret pair from [Spotify.](https://developer.spotify.com/dashboard)

## Configuration

You can configure Blanco using either a YAML file or environment variables. Configuration from environment variables takes precedence over configuration from the YAML file.

### Environment variables

The following table lists the environment variables that Blanco accepts:

| Variable name | Description | Type | Required? |
| ------------- | ----------- | ------ | --------- |
| BLANCO_DB_FILE | Path to SQLite database file | String | ✅ |
| BLANCO_TOKEN | Discord bot token | String | ✅ |
| BLANCO_SPOTIFY_ID | Spotify client ID | String | ✅ |
| BLANCO_SPOTIFY_SECRET | Spotify client secret | String | ✅ |
| BLANCO_ENABLE_SERVER | Whether to enable the webserver | `true` or `false` | |
| BLANCO_LASTFM_KEY | Last.fm API key | String | |
| BLANCO_LASTFM_SECRET | Last.fm API shared secret | String | |
| BLANCO_DEBUG | Whether to enable debug mode | `true` or `false` |  |
| BLANCO_DEBUG_GUILDS | Guild IDs to register slash commands in when debug mode is enabled | Comma-separated list of integers |  |

If `BLANCO_ENABLE_SERVER` is set to `true`, Blanco expects the following additional environment variables:

| Variable name | Description | Type | Required? |
| ------------- | ----------- | ------ | --------- |
| BLANCO_SERVER_PORT | Port that the webserver listens on | Integer | |
| BLANCO_BASE_URL | Webserver base URL | String | ✅ |
| BLANCO_OAUTH_ID | Discord OAuth client ID | String | ✅ |
| BLANCO_OAUTH_SECRET | Discord OAuth client secret | String | ✅ |

`BLANCO_SERVER_PORT` defaults to `8080`. Having this configurable is especially useful when running Blanco in host networking mode, e.g., when running Lavalink and Blanco in the same Docker host with IPv6 support enabled.

Additionally, Blanco expects the following environment variables to be set for each Lavalink node, where `n` in the variable name is an integer incrementing from 1:

| Variable name | Description | Required? | Format | Example |
| ------------- | ----------- | --------- | ------ | ------- |
| BLANCO_NODE_n | Node connection details | ✅ | `label:password@host:port` | `main:youshallnotpass@localhost:2333` |
| BLANCO_NODE_n_REGIONS | Node regions | ✅ | Comma-separated list of strings | `us-central,us-east` |
| BLANCO_NODE_n_SECURE | Whether the node supports SSL |  | `true` or `false` | `false` |
| BLANCO_NODE_n_DEEZER | Whether the node supports playback from Deezer via LavaSrc |  | `true` or `false` | `false` |

Make sure `n` is a unique integer for each node, and that you don't skip values of `n`.

### YAML file

Create an empty directory and create a file named `config.yml` in it, with the following contents:

```yaml
bot:
  database: blanco.db
  discord_token: <your Discord bot token>
  debug: # Optional
    enabled: true
    guild_ids:
      - 123456789012345678
server: # Optional
  enabled: false
  port: 8080
  base_url: http://localhost:8080
  oauth_id: <your Discord OAuth client ID>
  oauth_secret: <your Discord OAuth client secret>
spotify:
  client_id: <your client id>
  client_secret: <your client secret>
lastfm: # Optional
  api_key: <your Last.fm API key>
  shared_secret: <your Last.fm API shared secret>
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
    
    # Set to true if node supports playback from Deezer using LavaSrc
    deezer: false
# You may add more than one node here
# - id: backup
#   ...
```

Edit the values with your Discord and Spotify tokens, along with the details of your chosen Lavalink server(s).

### Database file

We also need to create an empty database file which will be used by the bot to store settings. Open a terminal in a folder of your choosing and run the following command:

```
# Windows cmd
type nul > blanco.db

# Linux, macOS, etc.
touch blanco.db
```

Then point the bot to the database file path by setting either the `BLANCO_DB_FILE` environment variable or the `bot.database` key in the YAML file.

## With Docker

Blanco comes in a Docker image, so you do not have to install anything aside from Docker. All of the dependencies are included in the Docker image, which has been tested on Linux hosts using Docker CE, and on Windows and macOS hosts using Docker Desktop.

Aside from `linux/amd64`, the bot image is also built with `linux/arm64/v8` support, so you can run the bot on a Raspberry Pi 3B+ or a Mac with Apple silicon with reasonable performance. `linux/armv7` images are no longer available starting with Release 0.4.0, but you are welcome to deploy Blanco without Docker if you need to run it on a Raspberry Pi 2 or older.

Make sure you followed [Prerequisites](#prerequisites), then create a `docker-compose.yml` file in the same folder with the following contents:

```yaml
version: '3.8'
services:
  blanco:
    container_name: blanco-bot
    restart: unless-stopped
    image: jareddantis/blanco-bot
    # OR image: ghcr.io/jareddantis-bots/blanco-bot

    environment:
      - BLANCO_DB_FILE=/opt/app/blanco.db
      - BLANCO_TOKEN=<your Discord bot token>
      - BLANCO_SPOTIFY_ID=<your Spotify client ID>
      - BLANCO_SPOTIFY_SECRET=<your Spotify client secret>
      # - BLANCO_DEBUG=true
      # - BLANCO_DEBUG_GUILDS=<your guild ID>
      - BLANCO_NODE_1=main:youshallnotpass@localhost:2333
      - BLANCO_NODE_1_REGIONS=us-central,us-east
      - BLANCO_NODE_1_SECURE=false
      - BLANCO_NODE_1_DEEZER=false
      # - BLANCO_NODE_2=...
    
    volumes:
      - /YOUR/PATH/HERE/blanco.db:/opt/app/blanco.db

      # You can omit this if you're using env variables
      - /YOUR/PATH/HERE/config.yml:/opt/app/config.yml
    
    # You can omit this if you're not using the webserver
    ports:
      - 8080:8080
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

or use [Watchtower](https://containrrr.dev/watchtower) to keep Blanco updated automatically.

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
6. Configure Blanco according to the instructions in [Prerequisites](#prerequisites).
7. If using the webserver, generate `server/static/css/main.css` by installing [Tailwind CLI](https://tailwindcss.com/blog/standalone-cli) and running
    ```
    tailwindcss -i ./server/static/css/base.css -o ./server/static/css/main.css --minify
    ```
8. Run Blanco using `python3 main.py`.

# Debugging mode

Blanco's debug mode, enabled through `BLANCO_DEBUG` or the config key `bot.debug.enabled`, is used to
- register slash commands in a specified guild instead of globally like normal, and
- print additional messages to the console, such as the songs played in every guild.

It is not recommended to enable debugging mode outside of testing, as the bot will also print sensitive information such as your Discord bot token and Spotify secrets to the console.
