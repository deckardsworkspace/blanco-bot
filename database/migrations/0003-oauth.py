from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlite3 import Connection

def run(con: 'Connection'):
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS discord_oauth (
            user_id INTEGER PRIMARY KEY NOT NULL,
            username TEXT NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS spotify_oauth (
            user_id INTEGER PRIMARY KEY NOT NULL,
            username TEXT NOT NULL,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            scopes TEXT NOT NULL DEFAULT ''
        )
    ''')
    con.commit()
