from aiohttp import web


async def index(request: web.Request):
    return web.Response(text=f'Hello, world!')
