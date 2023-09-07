"""
Delete account view (empty, redirects to logout).
"""

from aiohttp import web
from aiohttp_session import get_session


async def delete_account(request: web.Request):
    """
    Delete user data from all tables and redirect to logout.
    """
    # Get session
    session = await get_session(request)
    if 'user_id' not in session:
        return web.HTTPFound('/login')

    # Delete user data from all tables
    database = request.app['db']
    database.delete_oauth('discord', session['user_id'])
    database.delete_oauth('spotify', session['user_id'])
    database.delete_oauth('lastfm', session['user_id'])

    # Redirect to logout
    return web.HTTPFound('/logout')
