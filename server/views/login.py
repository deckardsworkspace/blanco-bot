from aiohttp import web
from yarl import URL


async def login(request: web.Request):
    # Get OAuth ID and base URL
    oauth_id = request.app['config'].discord_oauth_id
    base_url = request.app['config'].base_url

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
        }
    )

    # Redirect
    return web.HTTPFound(url)
