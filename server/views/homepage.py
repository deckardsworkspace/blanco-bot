from aiohttp import web
import aiohttp_jinja2


@aiohttp_jinja2.template('homepage.html')
async def homepage(_: web.Request):
    return {}
