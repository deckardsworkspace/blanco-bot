from fastapi import APIRouter

from .discord import discord_oauth as route_discord

oauth_router = APIRouter(prefix='/oauth', tags=['oauth'])
oauth_router.add_api_route('/discord', route_discord, methods=['GET'])
