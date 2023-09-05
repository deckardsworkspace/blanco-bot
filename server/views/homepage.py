from aiohttp import web
from aiohttp_session import get_session
import aiohttp_jinja2


@aiohttp_jinja2.template('homepage.html')
async def homepage(request: web.Request):
    # Get session
    session = await get_session(request)
    if 'user_id' in session:
        return web.HTTPFound('/dashboard')
    
    return {}
