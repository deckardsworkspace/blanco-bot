"""
Create tables for storing authentication data for Discord, Spotify and Last.fm.
"""
# pylint: disable=invalid-name

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlite3 import Connection

def run(con: 'Connection'):
    """
    Run the migration.
    """
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
    cur.execute('''
        CREATE TABLE IF NOT EXISTS lastfm_oauth (
            user_id INTEGER PRIMARY KEY NOT NULL,
            username TEXT NOT NULL,
            session_key TEXT NOT NULL
        )
    ''')
    con.commit()
