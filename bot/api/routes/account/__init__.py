from fastapi import APIRouter

from .login import get_login_url as route_login
from .me import get_logged_in_user as route_me

account_router = APIRouter(prefix='/account', tags=['account'])
account_router.add_api_route('/login', route_login, methods=['GET'])
account_router.add_api_route('/me', route_me, methods=['GET'])
