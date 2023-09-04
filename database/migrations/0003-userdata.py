from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlite3 import Connection

def run(con: 'Connection'):
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS userdata (
            user_id INTEGER PRIMARY KEY NOT NULL,
            username TEXT NOT NULL,
            discord_access_token TEXT NOT NULL,
            discord_refresh_token TEXT NOT NULL,
            discord_expires_at INTEGER NOT NULL,
            spotify_access_token TEXT NOT NULL DEFAULT '',
            spotify_refresh_token TEXT NOT NULL DEFAULT '',
            spotify_expires_at INTEGER NOT NULL DEFAULT 0,
            lastfm_username TEXT NOT NULL DEFAULT '',
            lastfm_session_key TEXT NOT NULL DEFAULT ''
        )
    ''')
    con.commit()
