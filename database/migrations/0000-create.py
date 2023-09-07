"""
Create the player_settings table. Introduced with the first version of Blanco.
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
        CREATE TABLE IF NOT EXISTS player_settings (
            guild_id INTEGER PRIMARY KEY NOT NULL,
            volume INTEGER NOT NULL DEFAULT 100,
            loop INTEGER NOT NULL DEFAULT 0,
            last_np_msg INTEGER NOT NULL DEFAULT -1
        )
    ''')
    con.commit()
