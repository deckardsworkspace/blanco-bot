from aiohttp import web
from aiohttp_session import get_session
from dataclass.oauth import LastfmAuth
from hashlib import md5
from .constants import LASTFM_API_BASE_URL, USER_AGENT
import requests


async def lastfm_token(request: web.Request):
    # Get session
    session = await get_session(request)

    # Get state and Discord user ID
    if 'user_id' not in session:
        return web.HTTPBadRequest(text='You are not logged into Blanco with Discord.')
    user_id = session['user_id']

    # Get API key and secret
    api_key = request.app['config'].lastfm_api_key
    secret = request.app['config'].lastfm_shared_secret

    # Get token
    try:
        token = request.query['token']
    except KeyError:
        return web.HTTPBadRequest(text='Missing token, try logging in again.')
    
    # Create signature
    signature = ''.join([
        'api_key',
        api_key,
        'method',
        'auth.getSession',
        'token',
        token,
        secret
    ])
    hashed = md5(signature.encode('utf-8')).hexdigest()

    # Get session key
    url = LASTFM_API_BASE_URL.with_query({
        'method': 'auth.getSession',
        'api_key': api_key,
        'token': token,
        'api_sig': hashed,
        'format': 'json'
    })

    # Get response
    response = requests.get(
        str(url),
        headers={
            'User-Agent': USER_AGENT
        }
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        return web.HTTPBadRequest(text=f'Error logging into Last.fm: {e}')
    
    # Get JSON
    json = response.json()
    try:
        session_key = json['session']['key']
        username = json['session']['name']
    except KeyError as e:
        return web.HTTPBadRequest(text=f'Error logging into Last.fm: missing {e.args[0]}')
    
    # Store user info in DB
    db = request.app['db']
    db.set_lastfm_credentials(LastfmAuth(
        user_id=user_id,
        username=username,
        session_key=session_key
    ))

    # Redirect to dashboard
    return web.HTTPFound('/dashboard')
