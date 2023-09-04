from typing import TYPE_CHECKING
from .views import index
if TYPE_CHECKING:
    from aiohttp.web import Application


def setup_routes(app: 'Application'):
    app.router.add_get('/', index)
