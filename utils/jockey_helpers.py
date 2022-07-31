from dataclass.custom_embed import CustomEmbed
from dataclass.queue_item import QueueItem
from itertools import islice
from lavalink.models import DefaultPlayer
from nextcord import Color, Embed, Interaction
from typing import Any, Coroutine, Optional
from .exceptions import SpotifyInvalidURLError
from .url_check import *
from .spotify_client import parse_spotify_url, Spotify
from .lavalink_client import *
import asyncio


def create_error_embed(message: str) -> Embed:
    embed = CustomEmbed(
        color=Color.red(),
        title=':x:｜Error processing command',
        description=message
    )
    return embed.get()


def create_success_embed(message: str) -> Embed:
    embed = CustomEmbed(
        color=Color.green(),
        title=':white_check_mark:｜Success',
        description=message
    )
    return embed.get()


def create_now_playing_embed(track: QueueItem, uri: Optional[str] = '') -> Embed:
    # Construct Spotify URL if it exists
    if track.spotify_id is not None:
        uri = f'https://open.spotify.com/track/{track.spotify_id}'

    embed = CustomEmbed(
        title='Now playing',
        description=[
            f'[**{track.title}**]({uri})',
            f'{track.artist}'
        ],
        color=Color.teal(),
        timestamp_now=True
    )
    return embed.get()


def list_chunks(data: List[Any]) -> List[Any]:
    for i in range(0, len(data), 10):
        yield islice(data, i, i + 10)


def manual_await(coro: Coroutine) -> Any:
    """
    Await a coroutine, but don't raise an exception if it fails.
    """
    try:
        task = asyncio.create_task(coro)
        return asyncio.get_event_loop().run_until_complete(task)
    except Exception:
        return None


async def parse_query(itx: Interaction, player: DefaultPlayer, spotify: Spotify, query: str) -> List[QueueItem]:
    if check_url(query):
        return await parse_query_url(itx, player, spotify, query)

    # Query is not a URL. Do a YouTube search for the query and choose the first result.
    try:
        result = await get_youtube_matches(player, query, automatic=False)[0]
    except IndexError:
        embed = CustomEmbed(
            color=Color.red(),
            title=':x:｜No results found for query'
        )
        await itx.followup.send(embed=embed.get())
        return []
    else:
        return [QueueItem(
            title=result.title,
            artist=result.author,
            requester=itx.user.id,
            duration=result.duration_ms,
            url=result.url
        )]


async def parse_query_url(itx: Interaction, player: DefaultPlayer, spotify: Spotify, query: str) -> List[QueueItem]:
    if check_spotify_url(query):
        # Query is a Spotify URL.
        return await parse_spotify_query(itx, spotify, query)

    if check_youtube_url(query):
        # Query is a YouTube URL.
        # Is it a playlist?
        try:
            playlist_id = get_ytlistid_from_url(query)

            # It is a playlist!
            # Let us get the playlist's tracks.
            return await parse_youtube_playlist(itx, player, playlist_id)
        except LavalinkInvalidPlaylistError as e:
            # No tracks found
            embed = CustomEmbed(
                color=Color.red(),
                title=':x:｜Error enqueueing YouTube playlist',
                description=e.message
            )
            await itx.followup.send(embed=embed.get())
            return []
        except:
            pass

        # Is it a video?
        try:
            video_id = get_ytid_from_url(query)

            # It is a video!
            # Let us get the video's details.
            video = await get_youtube_video(player, video_id)
            return [QueueItem(
                title=video.title,
                artist=video.author,
                requester=itx.user.id,
                duration=video.duration_ms,
                url=video.url,
                lavalink_track=video.lavalink_track
            )]
        except LavalinkInvalidURLError:
            embed = CustomEmbed(
                color=Color.red(),
                title=':x:｜Error enqueueing YouTube video',
                description='The video has either been deleted, or made private, or never existed.'
            )
            await itx.followup.send(embed=embed.get())
            return []
        except:
            embed = CustomEmbed(
                color=Color.red(),
                title=':x:｜YouTube URL is invalid',
                description=f'Only YouTube video and playlist URLs are supported.'
            )
            await itx.followup.send(embed=embed.get())
            return []

    # Query is a non-YouTube URL.
    return [QueueItem(
        requester=itx.user.id,
        url=query
    )]


async def parse_spotify_query(itx: Interaction, spotify: Spotify, query: str) -> List[QueueItem]:
    # Generally for Spotify tracks, we pick the YouTube result with
    # the same artist and title, and the closest duration to the Spotify track.
    try:
        sp_type, sp_id = parse_spotify_url(query, valid_types=['track', 'album', 'playlist'])
    except SpotifyInvalidURLError:
        embed = CustomEmbed(
            color=Color.red(),
            title=':x:｜Can only play tracks, albums, and playlists from Spotify.'
        )
        await itx.followup.send(embed=embed.get())
        return []
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
        return await itx.followup.send(embed=embed.get())

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
        await itx.channel.send(embed=embed.get())

    for track in track_queue:
        track_name, track_artist, track_id, track_duration = track
        new_tracks.append(QueueItem(
            requester=itx.user.id,
            title=track_name,
            artist=track_artist,
            spotify_id=track_id,
            duration=track_duration
        ))
    
    return new_tracks


async def parse_youtube_playlist(itx: Interaction, player: DefaultPlayer, playlist_id: str) -> List[QueueItem]:
    # Get playlist tracks from YouTube
    new_tracks = []
    try:
        playlist_name, tracks = await get_playlist(player, playlist_id)
    except:
        # No tracks.
        raise LavalinkInvalidPlaylistError(f'Playlist {playlist_id} is empty, private, or nonexistent')
    else:
        embed = CustomEmbed(
            color=Color.dark_red(),
            header=f'Enqueueing YouTube playlist',
            title=playlist_name,
            description=[f'[{len(tracks)} track(s)](http://youtube.com/playlist?list={playlist_id})'],
            footer='This might take a while, please wait...'
        )
        await itx.channel.send(embed=embed.get())

        for track in tracks:
            new_tracks.append(QueueItem(
                requester=itx.user.id,
                title=track.title,
                artist=track.author,
                duration=track.duration_ms,
                url=track.url,
                lavalink_track=track.lavalink_track
            ))

        return new_tracks
