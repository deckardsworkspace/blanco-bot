"""
Last.fm auth view.
"""

from aiohttp import web
from aiohttp_session import get_session
from yarl import URL


async def link_lastfm(request: web.Request):
    """
    Redirect to Last.fm auth flow.
    """
    # Create session
    session = await get_session(request)

    # Check if user is logged in
    if 'user_id' not in session:
        return web.HTTPFound('/login')

    # Get API key and base URL
    api_key = request.app['config'].lastfm_api_key
    base_url = request.app['config'].base_url

    # Redirect to Last.fm
    url = URL.build(
        scheme='https',
        host='www.last.fm',
        path='/api/auth',
        query={
            'api_key': api_key,
            'cb': f'{base_url}/lastfmtoken'
        }
    )
    return web.HTTPFound(url)
