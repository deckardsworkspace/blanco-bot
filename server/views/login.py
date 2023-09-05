from aiohttp import web
from aiohttp_session import get_session
from secrets import choice
from string import ascii_letters, digits
from yarl import URL


async def login(request: web.Request):
    # Create session
    session = await get_session(request)

    # Get OAuth ID and base URL
    oauth_id = request.app['config'].discord_oauth_id
    base_url = request.app['config'].base_url

    # Generate and store state
    state = ''.join(choice(ascii_letters + digits) for _ in range(16))
    session['state'] = state

    # Build URL
    url = URL.build(
        scheme='https',
        host='discord.com',
        path='/api/oauth2/authorize',
        query={
            'client_id': oauth_id,
            'response_type': 'code',
            'scope': 'identify guilds email',
            'redirect_uri': f'{base_url}/discordoauth',
            'state': state,
            'prompt': 'none'
        }
    )

    # Redirect to Discord
    return web.HTTPFound(url)
