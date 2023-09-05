from aiohttp import web
from aiohttp_session import get_session
from dataclass.oauth import OAuth
from time import time
from utils.constants import DISCORD_API_BASE_URL, USER_AGENT
import requests


async def discordoauth(request: web.Request):
    # Get session
    session = await get_session(request)

    # Get state
    if 'state' not in session:
        return web.HTTPBadRequest(text='Missing state, try logging in again.')
    state = session['state']
    
    # Get OAuth ID, secret, and base URL
    oauth_id = request.app['config'].discord_oauth_id
    oauth_secret = request.app['config'].discord_oauth_secret
    base_url = request.app['config'].base_url

    # Get code
    try:
        code = request.query['code']
        state = request.query['state']
    except KeyError as e:
        return web.HTTPBadRequest(text=f'Missing parameter: {e.args[0]}')

    # Check state
    if state != session['state']:
        return web.HTTPBadRequest(text='Invalid state, try logging in again.')
    
    # Get access token
    response = requests.post(
        str(DISCORD_API_BASE_URL / 'oauth2/token'),
        data={
            'client_id': oauth_id,
            'client_secret': oauth_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f'{base_url}/discordoauth'
        },
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': USER_AGENT
        }
    )
    try:
        response.raise_for_status()
    except Exception as e:
        return web.HTTPBadRequest(text=f'Error getting access token: {e}')

    # Get user info
    parsed = response.json()
    user_info = requests.get(
        str(DISCORD_API_BASE_URL / 'users/@me'),
        headers={
            'Authorization': f'Bearer {parsed["access_token"]}',
            'User-Agent': USER_AGENT
        }
    )
    try:
        user_info.raise_for_status()
    except Exception as e:
        return web.HTTPBadRequest(text=f'Error getting user info: {e}')
    
    # Calculate expiry timestamp
    user_parsed = user_info.json()
    expires_at = int(time()) + parsed['expires_in']

    # Store user info in DB
    db = request.app['db']
    db.set_oauth('discord', OAuth(
        user_id=user_parsed['id'],
        username=user_parsed['username'],
        access_token=parsed['access_token'],
        refresh_token=parsed['refresh_token'],
        expires_at=expires_at
    ))

    # Redirect to dashboard
    del session['state']
    session['user_id'] = user_parsed['id']
    return web.HTTPFound('/dashboard')
