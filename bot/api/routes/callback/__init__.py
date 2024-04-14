from fastapi import APIRouter

from .discord import discord_callback
from .lastfm import lastfm_callback
from .spotify import spotify_callback

callback_router = APIRouter(prefix='/callback', tags=['oauth'])
callback_router.add_api_route('/discord', discord_callback, methods=['GET'])
callback_router.add_api_route('/lastfm', lastfm_callback, methods=['GET'])
callback_router.add_api_route('/spotify', spotify_callback, methods=['GET'])
