from dataclass.custom_embed import CustomEmbed
from dataclass.queue_item import QueueItem
from itertools import islice
from lavalink.models import DefaultPlayer
from nextcord import Color, Embed, Interaction
from typing import Any, Coroutine, Optional
from .exceptions import SpotifyInvalidURLError, SpotifyNoResultsError
from .lavalink_client import *
from .spotify_client import Spotify
from .string_util import human_readable_time
from .url import *
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
    
    # Get track duration
    duration = None
    if track.duration != 0:
        h, m, s = human_readable_time(track.duration)
        duration = f'{s}s'
        if m > 0:
            duration = f'{m}m {duration}'
        if h > 0:
            duration = f'{h}h {duration}'

    embed = CustomEmbed(
        title='Now playing',
        description=[
            f'[**{track.title}**]({uri})',
            f'{track.artist}',
            duration
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
        if check_spotify_url(query):
            # Query is a Spotify URL.
            return await parse_spotify_query(itx, spotify, query)
        elif check_youtube_url(query):
            # Query is a YouTube URL.
            return await parse_youtube_query(itx, player, query)
        elif check_sc_url(query):
            # Query is a SoundCloud URL.
            return await parse_sc_query(itx, player, query)
        else:
            # Query is a non-YouTube URL.
            return [QueueItem(
                requester=itx.user.id,
                url=query
            )]

    # Query is not a URL. Try to find a match on Spotify.
    sp_title, sp_artist, sp_id, sp_duration = (None, None, None, None)
    try:
        sp_title, sp_artist, sp_id, sp_duration = spotify.search(query)
    except SpotifyNoResultsError:
        results = await get_youtube_matches(player, query, automatic=False)
    else:
        results = await get_youtube_matches(player, f'{sp_title} {sp_artist}', desired_duration_ms=sp_duration, automatic=True)

    # Play an equivalent on YouTube.
    try:
        result = results[0]
    except IndexError:
        embed = CustomEmbed(
            color=Color.red(),
            title=':x:｜No results found for query'
        )
        await itx.followup.send(embed=embed.get())
        return []
    else:
        return [QueueItem(
            title=sp_title if sp_title else result.title,
            artist=sp_artist if sp_artist else result.author,
            requester=itx.user.id,
            duration=sp_duration if sp_duration else result.duration_ms,
            url=result.url,
            spotify_id=sp_id,
            lavalink_track=result.lavalink_track
        )]


async def parse_sc_query(itx: Interaction, player: DefaultPlayer, query: str) -> List[QueueItem]:
    # Get entity type
    entity_type = get_sctype_from_url(query)

    try:
        # Get results with Lavalink
        set_name, tracks = await get_tracks(player, query)
    except:
        raise LavalinkInvalidIdentifierError(f'Entity {query} is private, nonexistent, or has no stream URL')
    else:
        if not entity_type:
            embed = CustomEmbed(
                color=Color.orange(),
                header=f'Enqueueing SoundCloud set',
                title=set_name,
                description=[
                    f'{len(tracks)} track(s)',
                    query
                ],
                footer='This might take a while, please wait...'
            )
            await itx.channel.send(embed=embed.get())

        return [QueueItem(
            requester=itx.user.id,
            title=track.title,
            artist=track.author,
            duration=track.duration_ms,
            url=track.url,
            lavalink_track=track.lavalink_track
        ) for track in tracks]


async def parse_spotify_query(itx: Interaction, spotify: Spotify, query: str) -> List[QueueItem]:
    # Generally for Spotify tracks, we pick the YouTube result with
    # the same artist and title, and the closest duration to the Spotify track.
    try:
        sp_type, sp_id = get_spinfo_from_url(query, valid_types=['track', 'album', 'playlist'])
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
                f'by **{list_author}**',
                f'{len(track_queue)} track(s)',
                query
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
    try:
        # Get playlist tracks from YouTube
        playlist_name, tracks = await get_tracks(player, playlist_id)
    except:
        # No tracks.
        raise LavalinkInvalidIdentifierError(f'Playlist {playlist_id} is empty, private, or nonexistent')
    else:
        embed = CustomEmbed(
            color=Color.dark_red(),
            header=f'Enqueueing YouTube playlist',
            title=playlist_name,
            description=[
                f'{len(tracks)} track(s)',
                f'https://youtube.com/playlist?list={playlist_id}'
            ],
            footer='This might take a while, please wait...'
        )
        await itx.channel.send(embed=embed.get())

        return [QueueItem(
            requester=itx.user.id,
            title=track.title,
            artist=track.author,
            duration=track.duration_ms,
            url=track.url,
            lavalink_track=track.lavalink_track
        ) for track in tracks]


async def parse_youtube_query(itx: Interaction, player: DefaultPlayer, query: str) -> List[QueueItem]:
    # Is it a playlist?
    try:
        playlist_id = get_ytlistid_from_url(query)

        # It is a playlist!
        # Let us get the playlist's tracks.
        return await parse_youtube_playlist(itx, player, playlist_id)
    except LavalinkInvalidIdentifierError as e:
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
        _, video = await get_tracks(player, video_id)
        return [QueueItem(
            title=video[0].title,
            artist=video[0].author,
            requester=itx.user.id,
            duration=video[0].duration_ms,
            url=video[0].url,
            lavalink_track=video[0].lavalink_track
        )]
    except LavalinkInvalidIdentifierError:
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
