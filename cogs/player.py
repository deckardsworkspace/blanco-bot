from asyncio import TimeoutError
from nextcord import Color, Guild, Interaction, Member, slash_command, SlashOption, VoiceState
from nextcord.abc import Messageable
from nextcord.ext import application_checks
from nextcord.ext.commands import Cog
from typing import Dict, Optional, TYPE_CHECKING
from dataclass.custom_embed import CustomEmbed
from utils.exceptions import EndOfQueueError, JockeyException, JockeyError
from utils.jockey import Jockey
from utils.jockey_helpers import create_error_embed, create_success_embed, list_chunks
from utils.blanco import BlancoBot
from utils.logger import create_logger
from utils.paginator import Paginator
from utils.player_checks import *
from utils.spotify_private import PrivateSpotify
from views.spotify_dropdown import SpotifyDropdownView
if TYPE_CHECKING:
    from dataclass.queue_item import QueueItem


class PlayerCog(Cog):
    def __init__(self, bot: BlancoBot):
        self._bot = bot
        self._spotify_clients: Dict[int, PrivateSpotify] = {}
        self._logger = create_logger(self.__class__.__name__, bot.debug)

        # Initialize Lavalink client instance
        if not bot.pool_initialized:
            bot.loop.create_task(bot.init_pool())
        
        self._logger.info(f'Loaded cog')
    
    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        # Get the player for this guild from cache
        jockey: Jockey = member.guild.voice_client # type: ignore

        # Stop playing if we're left alone
        if jockey is not None and len(jockey.channel.members) == 1 and after.channel is None: # type: ignore
            return await self._disconnect(jockey=jockey, reason='You left me alone :(')
    
    async def _get_jockey(self, itx: Interaction) -> Jockey:
        """
        Gets the Jockey instance for the specified guild.
        """
        jockey: Jockey = itx.guild.voice_client # type: ignore
        if jockey is None:
            if not itx.response.is_done():
                await itx.followup.send(embed=create_error_embed('Not connected to voice'))
            raise RuntimeError('[player] Attempted to access Jockey for a guild that is not connected to voice')
        
        return jockey
    
    def _get_spotify_client(self, user_id: int) -> Optional[PrivateSpotify]:
        """
        Gets a Spotify client instance for the specified user.
        """
        if user_id not in self._spotify_clients:
            assert self._bot.config is not None

            # Try to get credentials
            creds = self._bot.db.get_oauth('spotify', user_id)
            if creds is None:
                return None
            
            self._spotify_clients[user_id] = PrivateSpotify(
                config=self._bot.config,
                db=self._bot.db,
                credentials=creds
            )
            self._logger.debug(f'Created Spotify client for user {user_id}')
        
        return self._spotify_clients[user_id]
    
    async def _disconnect(
        self,
        jockey: Optional[Jockey] = None,
        itx: Optional[Interaction] = None,
        reason: Optional[str] = None
    ):
        # Destroy jockey instance
        if jockey is None:
            if itx is None:
                raise ValueError('[player::_disconnect] Either jockey or itx must be specified')
            jockey = await self._get_jockey(itx)
        await jockey.stop()
        await jockey.disconnect()

        # Send disconnection message
        embed = CustomEmbed(
            title=':wave:｜Disconnected from voice',
            description=reason
        ).get()

        # Try to send disconnection message
        try:
            if itx is not None:
                await itx.followup.send(embed=embed)
            else:
                guild_id = jockey.guild.id
                channel = self._bot.get_status_channel(guild_id)
                if channel is not None:
                    await channel.send(embed=embed)
        except:
            pass
    
    @slash_command(name='jump')
    @application_checks.check(check_mutual_voice)
    async def jump(self, itx: Interaction, position: int = SlashOption(description='Position to jump to', required=True)):
        """
        Jumps to the specified position in the queue.
        """
        jockey = await self._get_jockey(itx)

        # First check if the value is within range
        if position < 1 or position > len(jockey.queue):
            await itx.response.send_message(f'Specify a number from 1 to {str(len(jockey.queue))}.', ephemeral=True)
            return
        
        # Dispatch to jockey
        await itx.response.defer()
        await jockey.skip(index=position - 1, auto=False)
        await itx.followup.send(embed=create_success_embed(f'Jumped to track {str(position)}'))
    
    @slash_command(name='loop')
    @application_checks.check(check_mutual_voice)
    async def loop(self, itx: Interaction):
        """
        Loops the current track.
        """
        jockey = await self._get_jockey(itx)
        if not jockey.is_looping:
            jockey.is_looping = True
            return await itx.response.send_message(embed=create_success_embed('Looping current track'))
        return await itx.response.send_message(embed=create_success_embed('Already looping current track'))
    
    @slash_command(name='loopall')
    @application_checks.check(check_mutual_voice)
    async def loopall(self, itx: Interaction):
        """
        Loops the whole queue.
        """
        jockey = await self._get_jockey(itx)
        if not jockey.is_looping_all:
            jockey.is_looping_all = True
            return await itx.response.send_message(embed=create_success_embed('Looping entire queue'))
        return await itx.response.send_message(embed=create_success_embed('Already looping entire queue'))
    
    @slash_command(name='nowplaying')
    @application_checks.check(check_mutual_voice)
    async def now_playing(self, itx: Interaction):
        """
        Displays the currently playing track.
        """
        await itx.response.defer(ephemeral=True)
        jockey = await self._get_jockey(itx)
        embed = jockey.now_playing()
        await itx.followup.send(embed=embed)

    @slash_command(name='pause')
    @application_checks.check(check_mutual_voice)
    async def pause(self, itx: Interaction):
        """
        Pauses the current track.
        """
        # Dispatch to jockey
        await itx.response.defer(ephemeral=True)
        jockey = await self._get_jockey(itx)
        await jockey.pause()
        await itx.followup.send(embed=create_success_embed('Paused'))

    @slash_command(name='play')
    @application_checks.check(check_mutual_voice)
    async def play(self, itx: Interaction, query: str = SlashOption(description='Query string or URL', required=True)):
        """
        Play a song from a search query or a URL.
        If you want to unpause a paused player, use /unpause instead.
        """
        if (not isinstance(itx.user, Member) or not itx.user.voice or
            not itx.user.voice.channel or not isinstance(itx.guild, Guild)):
            return await itx.response.send_message(embed=create_error_embed(
                message='Connect to a server voice channel to use this command.'
            ), ephemeral=True)
        
        # Set status channel
        guild_id = itx.guild.id
        channel = itx.channel
        if not isinstance(channel, Messageable):
            raise RuntimeError('[player::play] itx.channel is not Messageable')
        self._bot.set_status_channel(guild_id, channel)
        
        # Connect to voice
        await itx.response.defer()
        vc = itx.user.voice.channel
        if itx.guild.voice_client is None:
            try:
                await vc.connect(cls=Jockey) # type: ignore
                await vc.guild.change_voice_state(channel=vc, self_deaf=True)
            except TimeoutError:
                return await itx.followup.send(embed=create_error_embed(
                    message='Timed out while connecting to voice. Try again later.'
                ))

        # Dispatch to jockey
        jockey = await self._get_jockey(itx)
        try:
            track_name = await jockey.play_impl(query, itx.user.id)
        except JockeyError as e:
            # Disconnect if we're not playing anything
            if not jockey.playing:
                await self._disconnect(itx=itx, reason=str(e))
        except JockeyException as e:
            await itx.followup.send(embed=create_error_embed(str(e)))
        else:
            return await itx.followup.send(embed=create_success_embed(
                title='Added to queue',
                body=track_name
            ))
    
    @slash_command(name='playlists')
    async def playlist(self, itx: Interaction):
        """
        Pick a Spotify playlist from your library to play.
        """
        if itx.user is None:
            return
        await itx.response.defer(ephemeral=True)
        
        # Check if the user has linked their Spotify account
        assert self._bot.config is not None
        if not self._bot.db.get_oauth('spotify', itx.user.id):
            return await itx.followup.send(embed=create_error_embed(
                message=f'Please link your Spotify account [here.]({self._bot.config.base_url})'
            ), ephemeral=True)
        
        # Create Spotify client
        spotify = self._get_spotify_client(itx.user.id)
        if spotify is None:
            return await itx.followup.send(embed=create_error_embed(
                message='Unable to get Spotify playlists. Try again later.'
            ), ephemeral=True)
        
        # Get the user's playlists
        playlists = spotify.get_user_playlists()
        if len(playlists) == 0:
            return await itx.followup.send(embed=create_error_embed(
                message='You have no playlists.'
            ), ephemeral=True)
        
        # Create dropdown
        view = SpotifyDropdownView(self._bot, playlists)
        await itx.followup.send(embed=create_success_embed(
            title='Pick a playlist',
            body='Select a playlist from the dropdown below.'
        ), view=view)

    @slash_command(name='previous')
    @application_checks.check(check_mutual_voice)
    async def previous(self, itx: Interaction):
        """
        Skip to the previous song.
        """
        # Dispatch to jockey
        await itx.response.defer()
        jockey = await self._get_jockey(itx)
        try:
            await jockey.skip(forward=False, auto=False)
        except Exception as e:
            embed = create_error_embed(f'Unable to rewind. Reason: {e}')
            await itx.followup.send(embed=embed)
    
    @slash_command(name='queue')
    @application_checks.check(check_mutual_voice)
    async def queue(self, itx: Interaction):
        """
        Displays the current queue.
        """
        if itx.guild is None:
            raise RuntimeError('[player::queue] itx.guild is None')
        await itx.response.defer()

        # Get jockey
        jockey = await self._get_jockey(itx)
        if len(jockey.queue) == 0:
            await itx.followup.send(embed=create_error_embed('Queue is empty'))
            return
        
        # Show loop status
        embed_header = [f'{len(jockey.queue)} total']
        if jockey.is_looping_all:
            embed_header.append(':repeat: Looping entire queue (`/unloopall` to disable)')
        
        # Show shuffle status
        queue = list(jockey.queue)
        current = jockey.current_index
        if jockey.is_shuffling:
            embed_header.append(':twisted_rightwards_arrows: Shuffling queue  (`/unshuffle` to disable)')
            current = jockey.shuffle_indices.index(current)

            # Get shuffled version of queue
            queue = [jockey.queue[i] for i in jockey.shuffle_indices]

        # Show queue in chunks of 10 per page
        pages = []
        homepage = 0
        count = 1
        prefix_len = len(str(len(jockey.queue)))
        for i, chunk in enumerate(list_chunks(queue)):
            chunk_tracks = []

            # Create page content
            track: 'QueueItem'
            for track in chunk:
                title, artist = track.get_details()

                # Pad index with spaces if necessary
                index = str(count)
                while len(index) < prefix_len:
                    index = ' ' + index
                
                # Is this the current track?
                line_prefix = '  '
                if count - 1 == current:
                    line_prefix = '> '
                    homepage = i
                
                # Create item line
                line_prefix = '> ' if count - 1 == current else '  '
                line = f'{line_prefix} {index} :: {title} - {artist}'

                # Truncate line if necessary
                if len(line) > 50:
                    line = line[:50] + '...'
                else:
                    line = f'{line:50.50}'
                chunk_tracks.append(line)
                count += 1

            # Create page
            tracks = '\n'.join(chunk_tracks)
            embed_body = embed_header + [f'```asciidoc\n{tracks}```']
            embed = CustomEmbed(
                title=f'Queue for {itx.guild.name}',
                description='\n'.join(embed_body),
                color=Color.lighter_gray()
            )
            pages.append(embed.get())
    
        # Run paginator
        paginator = Paginator(itx)
        return await paginator.run(pages, start=homepage)
    
    @slash_command(name='remove')
    @application_checks.check(check_mutual_voice)
    async def remove(
        self,
        itx: Interaction,
        position: int = SlashOption(
            description='Position to remove',
            required=True
        )
    ):
        """
        Remove a track from queue.
        """
        jockey = await self._get_jockey(itx)
        if position < 1 or position > jockey.queue_size:
            return await itx.response.send_message(embed=create_error_embed(
                message=f'Specify a number from 1 to {str(jockey.queue_size)}.'
            ), ephemeral=True)
        elif position - 1 == jockey.current_index:
            return await itx.response.send_message(embed=create_error_embed(
                message='You cannot remove the currently playing track.'
            ), ephemeral=True)
        
        # Dispatch to jockey
        await itx.response.defer()
        title, artist = await jockey.remove(index=position - 1)
        await itx.followup.send(embed=create_success_embed(
            title='Removed from queue',
            body=f'**{title}**\n{artist}'
        ))

    @slash_command(name='shuffle')
    @application_checks.check(check_mutual_voice)
    async def shuffle(self, itx: Interaction):
        """
        Shuffle the current playlist.
        If you want to unshuffle the current queue, use /unshuffle instead.
        """
        # Dispatch to jockey
        await itx.response.defer()
        jockey = await self._get_jockey(itx)
        try:
            await jockey.shuffle()
        except EndOfQueueError as e:
            await itx.followup.send(embed=create_error_embed(str(e)))
        else:
            await itx.followup.send(embed=create_success_embed(f'{len(jockey.queue)} tracks shuffled'))
    
    @slash_command(name='skip')
    @application_checks.check(check_mutual_voice)
    async def skip(self, itx: Interaction):
        """
        Skip the current song.
        """
        # Dispatch to jockey
        await itx.response.defer(ephemeral=True)
        jockey = await self._get_jockey(itx)
        try:
            await jockey.skip(auto=False)
        except Exception as e:
            embed = create_error_embed(f'Unable to skip. Reason: {e}')
            await itx.followup.send(embed=embed)
    
    @slash_command(name='stop')
    @application_checks.check(check_mutual_voice)
    async def stop(self, itx: Interaction):
        """
        Stops the current song and disconnects from voice.
        """
        if not isinstance(itx.user, Member):
            raise RuntimeError('[player::stop] itx.user is not a Member')
        await itx.response.defer()
        await self._disconnect(itx=itx, reason=f'Stopped by <@{itx.user.id}>')
    
    @slash_command(name='unloop')
    @application_checks.check(check_mutual_voice)
    async def unloop(self, itx: Interaction):
        """
        Stops looping the current track.
        """
        # Dispatch to jockey
        jockey = await self._get_jockey(itx)
        if jockey.is_looping:
            jockey.is_looping = False
            return await itx.response.send_message(embed=create_success_embed('Stopped looping current track'))
        return await itx.response.send_message(embed=create_success_embed('Not currently looping current track'))
    
    @slash_command(name='unloopall')
    @application_checks.check(check_mutual_voice)
    async def unloopall(self, itx: Interaction):
        """
        Stops looping the whole queue.
        """
        # Dispatch to jockey
        jockey = await self._get_jockey(itx)
        if jockey.is_looping_all:
            jockey.is_looping_all = False
            return await itx.response.send_message(embed=create_success_embed('Stopped looping entire queue'))
        return await itx.response.send_message(embed=create_success_embed('Not currently looping entire queue'))
    
    @slash_command(name='unpause')
    @application_checks.check(check_mutual_voice)
    async def unpause(self, itx: Interaction):
        """
        Unpauses the current track.
        """
        # Dispatch to jockey
        await itx.response.defer(ephemeral=True)
        jockey = await self._get_jockey(itx)
        await jockey.resume()
        await itx.followup.send(embed=create_success_embed('Unpaused'))

    @slash_command(name='unshuffle')
    @application_checks.check(check_mutual_voice)
    async def unshuffle(self, itx: Interaction):
        """
        Unshuffle the current playlist.
        """
        # Dispatch to jockey
        await itx.response.defer()
        jockey = await self._get_jockey(itx)
        if jockey.is_shuffling:
            jockey.shuffle_indices = []
            return await itx.followup.send(embed=create_success_embed('Unshuffled'))
        await itx.followup.send(embed=create_error_embed('Current queue is not shuffled'))
    
    @slash_command(name='volume')
    @application_checks.check(check_mutual_voice)
    async def volume(
        self,
        itx: Interaction,
        volume: Optional[int] = SlashOption(
            description='Volume level. Leave empty to print current volume.',
            required=False,
            min_value=0,
            max_value=1000
        )
    ):
        """
        Sets the volume level.
        """
        jockey = await self._get_jockey(itx)

        # Is the volume argument empty?
        if not volume:
            # Print current volume
            return await itx.response.send_message(f'The volume is set to {jockey.volume}.', ephemeral=True)

        # Dispatch to jockey
        await itx.response.defer()
        await jockey.set_volume(volume)
        await itx.followup.send(embed=create_success_embed(f'Volume set to {volume}'))
