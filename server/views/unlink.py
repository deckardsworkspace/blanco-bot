"""
Account unlinking view.
"""

from aiohttp import web
from aiohttp_session import get_session


async def unlink(request: web.Request):
    """
    Delete authentication data for the user from the specified service.
    """
    # Get session
    session = await get_session(request)
    if 'user_id' not in session:
        return web.HTTPFound('/login')
    user_id = session['user_id']

    # Get user info
    database = request.app['db']
    user = database.get_oauth('discord', user_id)
    if user is None:
        return web.HTTPFound('/login')

    # Which service to unlink?
    try:
        service = request.query['service']
    except KeyError as err:
        return web.HTTPBadRequest(text=f'Missing parameter: {err.args[0]}')

    if service not in ('lastfm', 'spotify'):
        raise web.HTTPBadRequest(text=f'Unknown service: {service}')

    database.delete_oauth(service, user_id)

    # Redirect to dashboard
    return web.HTTPFound('/dashboard')
