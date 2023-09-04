from aiohttp import web
from aiohttp_session import get_session
import aiohttp_jinja2


@aiohttp_jinja2.template('dashboard.html')
async def dashboard(request: web.Request):
    # Get session
    session = await get_session(request)
    if 'user_id' not in session:
        return web.HTTPFound('/login')
    
    # Get user info
    db = request.app['db']
    username = db.get_username(session['user_id'])
    if username is None:
        return web.HTTPFound('/login')
    
    # Render template
    return {
        'username': username
    }