blanco-bot
===

<img align="right" src="/server/static/images/logo.svg" width=200 alt="Blanco logo">

Blanco is a Discord music bot made with [Nextcord](https://nextcord.dev) that supports pulling music metadata from Spotify and scrobbling to Last.fm. Music playback is handled by the [Mafic](https://github.com/ooliver1/mafic) client for the [Lavalink](https://github.com/lavalink-devs/Lavalink) server.

[![GitHub Releases](https://img.shields.io/github/v/release/jareddantis-bots/blanco-bot)](https://github.com/jareddantis-bots/blanco-bot/releases/latest)
[![Docker Image CI](https://github.com/jareddantis/blanco-bot/actions/workflows/build.yml/badge.svg)](https://github.com/jareddantis/blanco-bot/actions/workflows/build.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/jareddantis/blanco-bot)](https://hub.docker.com/r/jareddantis/blanco-bot)

The bot stores data in a local SQLite database. This database is populated automatically on first run, and the data it will contain include authentication tokens, Lavalink session IDs, volume levels, and queue repeat preferences per guild.

- [blanco-bot](#blanco-bot)
- [Deployment](#deployment)
  - [Debugging mode](#debugging-mode)

# Deployment

> [!Warning]
> **Do not monetize, or attempt to submit for verification, any instance of this bot.** The Lavalink audio server has the ability to pull audio data from YouTube, which goes against the [YouTube Terms of Service,](https://www.youtube.com/t/terms) and optionally Deezer, which goes against the [Deezer Terms of Use.](https://www.deezer.com/legal/cgu)
>
> At best, Discord will reject your application for verification, and at worst, your developer account will get banned.

Head over to the [wiki](https://github.com/jareddantis-bots/blanco-bot/wiki/Deployment) to get started.

## Debugging mode

Blanco's debug mode, enabled through `BLANCO_DEBUG` or the config key `bot.debug.enabled`, is used to
- register slash commands in a specified guild instead of globally like normal, and
- print additional messages to the console, such as the songs played in every guild.

It is not recommended to enable debugging mode outside of testing, as the bot will also print sensitive information such as your Discord bot token and Spotify secrets to the console.
