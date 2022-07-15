from types import coroutine
from dataclass.custom_embed import CustomEmbed
from dataclass.queue_item import QueueItem
from nextcord import Color
from typing import Any
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
