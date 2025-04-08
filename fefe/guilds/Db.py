import discord 
import os 
from pathlib import Path
import sqlite3 
import aiosqlite
import logging

# script_path = os.path.dirname(os.path.abspath(__file__))
# Replace with pathlib equivalent
script_path = Path(__file__).parent 
bot_home_dir = script_path.parent / '..' /'..' 
data_dir = script_path / '../data'  
if not data_dir.exists():
    data_dir.mkdir(parents=True)
class GuildDB:
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.module_path = script_path
        self.data_dir = data_dir
        self.bot_home_dir = bot_home_dir
        self.guild_dir = data_dir / str(guild.id)
        if not self.guild_dir.exists():
            self.guild_dir.mkdir(parents=True)
        self.db_path = self.guild_dir / f'{guild.id}.db'
        # Initialize the database if it doesn't exist
        if not self.db_path.exists():
            self.initialize(guild)

    def connect_sync(self):
        """
        Connect to the SQLite database synchronously.
        """
        conn = sqlite3.connect(self.db_path)
        return conn
    
    async def connect(self):
        """
        Connect to the SQLite database asynchronously.
        """
        conn = await aiosqlite.connect(self.db_path)
        return conn
    def initialize(self, guild):
        conn = self.connect_sync()
        # Create the chat history table
        from fefe.channels.Tables import ChatHistoryTable
        chat_history_table = ChatHistoryTable()
        conn.execute(chat_history_table.CREATE)

        # Create the guild settings table
        from fefe.guilds.Tables import GuildSettingsTable
        guild_settings_table = GuildSettingsTable(guild)
        conn.execute(guild_settings_table.CREATE)
        # Initialize default settings for the guild
        conn.execute(guild_settings_table.INITIATE)

        conn.commit()
        conn.close()
        logging.info(f"Database initialized for guild {guild.id} at {self.db_path}")