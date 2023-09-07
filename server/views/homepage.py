"""
Homepage view.
"""

import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session


@aiohttp_jinja2.template('homepage.html')
async def homepage(request: web.Request):
    """
    Render the homepage, or redirect to the dashboard if the user is logged in.
    """
    # Get session
    session = await get_session(request)
    if 'user_id' in session:
        return web.HTTPFound('/dashboard')

    return {}
