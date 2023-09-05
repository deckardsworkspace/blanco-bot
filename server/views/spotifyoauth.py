from aiohttp import web
from aiohttp_session import get_session
from base64 import b64encode
from dataclass.oauth import OAuth
from time import time
from utils.constants import SPOTIFY_ACCOUNTS_BASE_URL, SPOTIFY_API_BASE_URL, USER_AGENT
import requests


async def spotifyoauth(request: web.Request):
    # Get session
    session = await get_session(request)

    # Get state and Discord user ID
    if 'state' not in session:
        return web.HTTPBadRequest(text='Missing state, try logging in again.')
    if 'user_id' not in session:
        return web.HTTPBadRequest(text='You are not logged into Blanco with Discord.')
    state = session['state']
    user_id = session['user_id']
    
    # Get OAuth ID, secret, and base URL
    oauth_id = request.app['config'].spotify_client_id
    oauth_secret = request.app['config'].spotify_client_secret
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
        str(SPOTIFY_ACCOUNTS_BASE_URL / 'token'),
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f'{base_url}/spotifyoauth'
        },
        headers={
            'Authorization': f'Basic {b64encode(f"{oauth_id}:{oauth_secret}".encode()).decode()}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': USER_AGENT
        }
    )
    try:
        response.raise_for_status()
    except Exception as e:
        return web.HTTPBadRequest(text=f'Error getting Spotify access token: {e}')

    # Get user info
    parsed = response.json()
    user_info = requests.get(
        str(SPOTIFY_API_BASE_URL / 'me'),
        headers={
            'Authorization': f'Bearer {parsed["access_token"]}',
            'User-Agent': USER_AGENT
        }
    )
    try:
        user_info.raise_for_status()
    except Exception as e:
        return web.HTTPBadRequest(text=f'Error getting Spotify user info: {e}')
    
    # Calculate expiry timestamp
    user_parsed = user_info.json()
    expires_at = int(time()) + parsed['expires_in']
    
    # Store user info in DB
    db = request.app['db']
    db.set_oauth('spotify', OAuth(
        user_id=user_id,
        username=user_parsed['id'],
        access_token=parsed['access_token'],
        refresh_token=parsed['refresh_token'],
        expires_at=expires_at
    ))
    db.set_spotify_scopes(user_id, parsed['scope'].split(' '))

    # Redirect to dashboard
    del session['state']
    return web.HTTPFound('/dashboard')
