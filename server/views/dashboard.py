from aiohttp import web
from aiohttp_session import get_session
from typing import TYPE_CHECKING
import aiohttp_jinja2
if TYPE_CHECKING:
    from dataclass.oauth import OAuth


@aiohttp_jinja2.template('dashboard.html')
async def dashboard(request: web.Request):
    # Get session
    session = await get_session(request)
    if 'user_id' not in session:
        return web.HTTPFound('/login')
    
    # Get user info
    db = request.app['db']
    user: OAuth = db.get_oauth('discord', session['user_id'])
    if user is None:
        return web.HTTPFound('/login')
    
    # Render template
    return {
        'username': user.username
    }