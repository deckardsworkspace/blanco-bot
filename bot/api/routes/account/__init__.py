from fastapi import APIRouter

from .delete import delete_account
from .lastfm import redirect_to_lastfm_login
from .login import redirect_to_login
from .logout import logout
from .me import get_logged_in_user
from .spotify import redirect_to_spotify_login
from .unlink import unlink_service

account_router = APIRouter(prefix='/account', tags=['account'])
account_router.add_api_route('/delete', delete_account, methods=['GET'])
account_router.add_api_route('/lastfm', redirect_to_lastfm_login, methods=['GET'])
account_router.add_api_route('/login', redirect_to_login, methods=['GET'])
account_router.add_api_route('/logout', logout, methods=['GET'])
account_router.add_api_route('/me', get_logged_in_user, methods=['GET'])
account_router.add_api_route('/spotify', redirect_to_spotify_login, methods=['GET'])
account_router.add_api_route('/unlink', unlink_service, methods=['POST'])
