"""
Create the lavalink table, which stores the session id for each node,
which are used to resume existing sessions across bot restarts.
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
  cur.execute("""
        CREATE TABLE IF NOT EXISTS lavalink (
            node_id TEXT PRIMARY KEY NOT NULL,
            session_id TEXT NOT NULL
        )
    """)
  con.commit()
