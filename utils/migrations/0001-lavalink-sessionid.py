from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlite3 import Connection

def run(con: 'Connection'):
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS lavalink (
            node_id TEXT PRIMARY KEY NOT NULL,
            session_id TEXT NOT NULL
        )
    ''')
    con.commit()
