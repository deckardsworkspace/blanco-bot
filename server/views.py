from aiohttp import web
import aiohttp_jinja2
import yarl


@aiohttp_jinja2.template('homepage.html')
async def homepage(request: web.Request):
    return {}


async def login(request: web.Request):
    # Get OAuth ID and base URL
    oauth_id = request.app['config'].discord_oauth_id
    base_url = request.app['config'].base_url

    # Build URL
    url = yarl.URL.build(
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
