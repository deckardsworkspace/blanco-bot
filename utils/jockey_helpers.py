from dataclass.custom_embed import CustomEmbed
from dataclass.queue_item import QueueItem
from nextcord import Color


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
