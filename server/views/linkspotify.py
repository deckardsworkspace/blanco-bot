from aiohttp import web
from aiohttp_session import get_session
from secrets import choice
from string import ascii_letters, digits
from yarl import URL


async def link_spotify(request: web.Request):
    # Create session
    session = await get_session(request)

    # Check if user is logged in
    if 'user_id' not in session:
        return web.HTTPFound('/login')

    # Get OAuth ID and base URL
    oauth_id = request.app['config'].spotify_client_id
    base_url = request.app['config'].base_url

    # Generate and store state
    state = ''.join(choice(ascii_letters + digits) for _ in range(16))
    session['state'] = state

    # Build URL
    scopes = [
        'user-read-private',        # Get username
        'user-read-email',          # Also for username, weirdly
        'user-library-modify',      # Add/remove Liked Songs
        'user-top-read',            # Get top tracks, for recommendations/radio
        'playlist-read-private'     # Get owned playlists
    ]
    url = URL.build(
        scheme='https',
        host='accounts.spotify.com',
        path='/authorize',
        query={
            'client_id': oauth_id,
            'response_type': 'code',
            'scope': ' '.join(scopes),
            'redirect_uri': f'{base_url}/spotifyoauth',
            'state': state
        }
    )

    # Redirect to Discord
    return web.HTTPFound(url)
