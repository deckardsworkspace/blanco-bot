from types import coroutine
from dataclass.custom_embed import CustomEmbed
from dataclass.queue_item import QueueItem
from nextcord import Color
from nextcord.ext.commands import Context
from typing import Any
from .exceptions import SpotifyInvalidURLError
from .url_check import *
from .spotify_client import parse_spotify_url, Spotify
from .youtube_client import *
import asyncio


def create_now_playing_embed(track: QueueItem) -> CustomEmbed:
    embed = CustomEmbed(
        title='Now playing',
        description=[
            f'**{track.title}**',
            f'by **{track.artist}**'
            f'requested by <@{track.requester}>'
        ],
        color=Color.teal(),
        timestamp_now=True
    )
    return embed.get()


def manual_await(coro: coroutine) -> Any:
    """
    Await a coroutine, but don't raise an exception if it fails.
    """
    try:
        task = asyncio.create_task(coro)
        return asyncio.get_event_loop().run_until_complete(task)
    except Exception:
        return None


async def parse_query(ctx: Context, spotify: Spotify, query: str) -> List[QueueItem]:
    if check_url(query):
        return await parse_query_url(ctx, spotify, query)

    # Query is not a URL. Do a YouTube search for the query and choose the first result.
    result = get_youtube_matches(query, automatic=False)[0]
    return [QueueItem(
        title=result.title,
        artist=result.author,
        requester=ctx.author.id,
        url=result.url
    )]


async def parse_query_url(ctx: Context, spotify: Spotify, query: str) -> List[QueueItem]:
    if check_spotify_url(query):
        # Query is a Spotify URL.
        return await parse_spotify_query(ctx, spotify, query)

    if check_youtube_url(query):
        # Query is a YouTube URL.
        # Is it a playlist?
        try:
            playlist_id = get_ytlistid_from_url(query)

            # It is a playlist!
            # Let us get the playlist's tracks.
            return await parse_youtube_playlist(ctx, playlist_id)
        except YouTubeInvalidPlaylistError as e:
            # No tracks found
            embed = CustomEmbed(
                color=Color.red(),
                title=':x:｜Error enqueueing YouTube playlist',
                description=e.message
            )
            await embed.send(ctx, as_reply=True)
        except:
            pass

        # Is it a video?
        try:
            video_id = get_ytid_from_url(query)

            # It is a video!
            # Let us get the video's details.
            video = get_youtube_video(video_id)
            return [QueueItem(
                title=video.title,
                artist=video.author,
                requester=ctx.author.id,
                url=video.url
            )]
        except YouTubeInvalidURLError:
            embed = CustomEmbed(
                color=Color.red(),
                title=':x:｜Error enqueueing YouTube video',
                description='The video has either been deleted, or made private, or never existed.'
            )
            await embed.send(ctx, as_reply=True)
            return []
        except:
            embed = CustomEmbed(
                color=Color.red(),
                title=':x:｜YouTube URL is invalid',
                description=f'Only YouTube video and playlist URLs are supported.'
            )
            await embed.send(ctx)
            return []

    # Query is a non-Spotify URL.
    return [QueueItem(
        requester=ctx.author.id,
        url=query
    )]


async def parse_spotify_query(ctx: Context, spotify: Spotify, query: str) -> List[QueueItem]:
    # Generally for Spotify tracks, we pick the YouTube result with
    # the same artist and title, and the closest duration to the Spotify track.
    try:
        sp_type, sp_id = parse_spotify_url(query, valid_types=['track', 'album', 'playlist'])
    except SpotifyInvalidURLError:
        embed = CustomEmbed(
            color=Color.red(),
            title=':x:｜Can only play tracks, albums, and playlists from Spotify.'
        )
        return await embed.send(ctx, as_reply=True)
    else:
        # Get artwork for Spotify track/album/playlist
        sp_art = ''
        if sp_type == 'album':
            sp_art = spotify.get_album_art(sp_id)
        elif sp_type == 'playlist':
            sp_art = spotify.get_playlist_cover(sp_id, default='')

    new_tracks = []
    if sp_type == 'track':
        # Get track details from Spotify
        track_queue = [spotify.get_track(sp_id)]
    else:
        # Get playlist or album tracks from Spotify
        list_name, list_author, track_queue = spotify.get_tracks(sp_type, sp_id)

    if len(track_queue) < 1:
        # No tracks.
        return await ctx.reply(f'Spotify {sp_type} is empty.')

    # At least one track.
    # Send embed if the list is longer than 1 track.
    if len(track_queue) > 1:
        embed = CustomEmbed(
            color=Color.green(),
            header=f'Enqueueing Spotify {sp_type}',
            title=list_name,
            description=[
                f'by **[{list_author}]({query})**',
                f'{len(track_queue)} track(s)'
            ],
            footer='This might take a while, please wait...',
            thumbnail_url=sp_art
        )
        await embed.send(ctx)

    for track in track_queue:
        track_name, track_artist, track_id, track_duration = track
        new_tracks.append(QueueItem(
            requester=ctx.author.id,
            title=track_name,
            artist=track_artist,
            spotify_id=track_id,
            duration=track_duration
        ))
    
    return new_tracks


async def parse_youtube_playlist(ctx: Context, playlist_id: str) -> List[QueueItem]:
    # Get playlist tracks from YouTube
    new_tracks = []
    playlist_name, playlist_author, num_tracks = get_youtube_playlist_info(playlist_id)
    if num_tracks < 1:
        # No tracks.
        raise YouTubeInvalidPlaylistError(f'Playlist {playlist_id} is empty.')

    # At least one track.
    # Send embed if the list is longer than 1 track.
    if num_tracks > 1:
        embed = CustomEmbed(
            color=Color.dark_red(),
            header=f'Enqueueing YouTube playlist',
            title=playlist_name,
            description=[
                f'by [{playlist_author}](http://youtube.com/playlist?list={playlist_id})',
                f'{num_tracks} track(s)'
            ],
            footer='This might take a while, please wait...'
        )
        await embed.send(ctx)

    tracks = get_youtube_playlist_tracks(playlist_id)
    for track in tracks:
        new_tracks.append(QueueItem(
            requester=ctx.author.id,
            title=track.title,
            artist=track.author,
            url=track.url
        ))

    return new_tracks
