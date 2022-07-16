import sqlite3 as sql


class Database:
    """
    Class for handling connections to the bot's SQLite DB.
    """

    def __init__(self, db_filename: str):
        self._con = sql.connect(db_filename)
        self._cur = self._con.cursor()

        # Create table if it doesn't exist yet
        self._cur.execute('''
            CREATE TABLE IF NOT EXISTS player_settings (
                guild_id INTEGER PRIMARY KEY NOT NULL,
                volume INTEGER NOT NULL DEFAULT 100,
                loop INTEGER NOT NULL DEFAULT 0,
                last_np_msg INTEGER NOT NULL DEFAULT -1
            )
        ''')
        self._con.commit()

        print(f'Connected to database: {db_filename}')
    
    def init_guild(self, guild_id: int):
        """
        Initialize a guild in the database if it hasn't been yet.
        """
        self._cur.execute(f'INSERT OR IGNORE INTO player_settings (guild_id) VALUES ({guild_id})')
        self._con.commit()
    
    def get_volume(self, guild_id: int) -> int:
        """
        Get the volume for a guild.
        """
        self._cur.execute(f'SELECT volume FROM player_settings WHERE guild_id = {guild_id}')
        return self._cur.fetchone()[0]
    
    def set_volume(self, guild_id: int, volume: int):
        """
        Set the volume for a guild.
        """
        self._cur.execute(f'UPDATE player_settings SET volume = {volume} WHERE guild_id = {guild_id}')
        self._con.commit()
    
    def get_loop(self, guild_id: int) -> bool:
        """
        Get the loop setting for a guild.
        """
        self._cur.execute(f'SELECT loop FROM player_settings WHERE guild_id = {guild_id}')
        return self._cur.fetchone()[0] == 1
    
    def set_loop(self, guild_id: int, loop: bool):
        """
        Set the loop setting for a guild.
        """
        self._cur.execute(f'UPDATE player_settings SET loop = {int(loop)} WHERE guild_id = {guild_id}')
        self._con.commit()
    
    def get_now_playing(self, guild_id: int) -> int:
        """
        Get the last now playing message ID for a guild.
        """
        self._cur.execute(f'SELECT last_np_msg FROM player_settings WHERE guild_id = {guild_id}')
        return self._cur.fetchone()[0]
    
    def set_now_playing(self, guild_id: int, msg_id: int):
        """
        Set the last now playing message ID for a guild.
        """
        self._cur.execute(f'UPDATE player_settings SET last_np_msg = {msg_id} WHERE guild_id = {guild_id}')
        self._con.commit()
