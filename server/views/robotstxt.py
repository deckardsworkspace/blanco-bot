"""
View for robots.txt
"""

from aiohttp import web


async def robotstxt(_: web.Request):
    """
    Return robots.txt
    """
    return web.Response(text='\n'.join([
        'User-agent: *',
        'Allow: /$',      # Allow homepage
        'Disallow: /'     # Disallow everything else
    ]))
