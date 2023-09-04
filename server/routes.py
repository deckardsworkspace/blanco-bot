from typing import TYPE_CHECKING
from .views import *
if TYPE_CHECKING:
    from aiohttp.web import Application


def setup_routes(app: 'Application'):
    app.router.add_get('/', homepage)
    app.router.add_static('/static/', path='server/static', name='static')
