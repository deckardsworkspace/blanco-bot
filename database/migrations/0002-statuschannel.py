"""
Add a column to the player_settings table to store the status channel ID.
"""
# pylint: disable=invalid-name

from sqlite3 import OperationalError
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlite3 import Connection

def run(con: 'Connection'):
    """
    Run the migration.
    """
    cur = con.cursor()

    # There's no built-in way to check if a column exists in SQLite,
    # so we just try to add it and ignore the error if it already exists.
    try:
        cur.execute('''
            ALTER TABLE player_settings ADD COLUMN status_channel INTEGER NOT NULL DEFAULT -1
        ''')
    except OperationalError:
        pass

    con.commit()
