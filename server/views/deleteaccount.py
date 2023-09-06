from aiohttp import web
from aiohttp_session import get_session


async def delete_account(request: web.Request):
    # Get session
    session = await get_session(request)
    if 'user_id' not in session:
        return web.HTTPFound('/login')
    
    # Delete user data from all tables
    db = request.app['db']
    db.delete_oauth('discord', session['user_id'])
    db.delete_oauth('spotify', session['user_id'])
    db.delete_oauth('lastfm', session['user_id'])

    # Redirect to logout
    return web.HTTPFound('/logout')
