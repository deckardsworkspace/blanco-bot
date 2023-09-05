from aiohttp import web
from aiohttp_session import get_session


async def logout(request: web.Request):
    # Get session
    session = await get_session(request)

    # Clear session
    session.clear()

    # Redirect to home
    return web.HTTPFound('/')
