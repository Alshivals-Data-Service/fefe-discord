import os 
import sqlite3
import aiosqlite
from discord.client import Client
from discord.message import Message
from discord.ext.commands import Context
from discord import Interaction
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function
import logging

def MessageInfo(message, client):
    params = {}
    if isinstance(message, (Context, Message)):
        # For Context and Message, we can access the author and channel directly
        params['author_name'] = message.author.name
        params['author_id'] = message.author.id
        params['guild_name'] = message.guild.name
        params['guild_id'] = message.guild.id
        params['channel_name'] = message.channel.name
        params['channel_id'] = message.channel.id

    elif isinstance(message, Interaction):
        params['author_name'] = message.user.name
        params['author_id'] = message.user.id
        params['guild_name'] = message.guild.name
        params['guild_id'] = message.guild.id
        params['channel_name'] = message.channel.name
        params['channel_id'] = message.channel.id
    else:
        raise TypeError("Unsupported message type. Expected Context, Interaction, or Message.")
    
    if message.author == client.user:
        role = 'assistant'
    else:
        role = 'user'
    params['role'] = role
    message_obj = str({'role': role, 'content': str(message.content)})
    row = {
            'guild_id': params['guild_id'],
            'guild_name': params['guild_name'],
            'channel_id': params['channel_id'],
            'channel_name': params['channel_name'],
            'author_id': params['author_id'],
            'author_name': params['author_name'],
            'message': message_obj
        }
    return row
    

class DatabaseConnector:
    def __init__(self,db_filename='fefe.db', initialize=False):
        self.module_path = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.module_path, db_filename)
        if initialize:
            self.initialize()
            logging.info(f"[Sync] Database initialized at {self.db_path}")

    def connect_sync(self):
        return sqlite3.connect(self.db_path)
    
    async def connect(self):
        return await aiosqlite.connect(self.db_path)
    
    def initialize(self):
        with self.connect_sync() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    guild_name TEXT,
                    channel_id TEXT,
                    channel_name TEXT,
                    author_id TEXT,
                    author_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message TEXT NOT NULL
                )
            ''')
            class ChatHistoryRow:
                def __init__(self, guild_id, guild_name, channel_id, channel_name, author_id, author_name, message):
                    self.guild_id = guild_id
                    self.guild_name = guild_name
                    self.channel_id = channel_id
                    self.channel_name = channel_name
                    self.author_id = author_id
                    self.author_name = author_name
                    self.message = message

                def __repr__(self):
                    return f"ChatHistoryRow(guild_id={self.guild_id}, guild_name={self.guild_name}, channel_id={self.channel_id}, channel_name={self.channel_name}, author_id={self.author_id}, author_name={self.author_name}, message={self.message})"
                def __getitem__(self, key):
                    return getattr(self, key)
                def __setitem__(self, key, value):
                    setattr(self, key, value)

            # Create a table for guild-level settings
            conn.execute('''
                CREATE TABLE IF NOT EXISTS guild_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    guild_name TEXT,
                    setting_name TEXT,
                    setting_value TEXT NOT NULL,
                    set_by TEXT DEFAULT 'system',
                    modified_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                         )''')
            class GuildSettingsRow:
                def __init__(self, guild_id, guild_name, setting_name, setting_value, set_by):
                    self.guild_id = guild_id
                    self.guild_name = guild_name
                    self.setting_name = setting_name
                    self.setting_value = setting_value
                    self.set_by = set_by

                def __repr__(self):
                    return f"GuildSettingsRow(guild_id={self.guild_id}, guild_name={self.guild_name}, setting_name={self.setting_name}, setting_value={self.setting_value}, set_by={self.set_by})"
                
                def __getitem__(self, key):
                    return getattr(self, key)
                
                def __setitem__(self, key, value):
                    setattr(self, key, value)

                def to_dict(self):
                    return {
                        'guild_id': self.guild_id,
                        'guild_name': self.guild_name,
                        'setting_name': self.setting_name,
                        'setting_value': self.setting_value,
                        'set_by': self.set_by
                    }

            # Create a table for channel-level settings
            conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    guild_name TEXT,
                    channel_id TEXT,
                    channel_name TEXT,
                    setting_name TEXT,
                    setting_value TEXT NOT NULL,
                    set_by TEXT DEFAULT 'system',
                    modified_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                         )''')
    ######################################################################
    # Guild Settings
    ######################################################################
    class DefaultGuildSettings:
        def __init__(self):
            self.personality = "You are a friendly and helpful waifu."
            self.model = "gpt-4o-mini"

    async def guild_settings(self, guild_id: str, guild_name: str = None):
        conn = await self.connect()
        query = f'''
            SELECT setting_name, setting_value FROM guild_settings WHERE guild_id = '{guild_id}'
        '''
        if guild_name:
            query += f" AND guild_name = '{guild_name}'"
        cursor = await conn.execute(query)
        rows = await cursor.fetchall()
        # If none, set default settings
        if not rows:
            # Set app_name to 'Fefe' if not provided


        await conn.close()
        return {row[0]: row[1] for row in rows} if rows else {}
    async def channel_settings(self, guild_id: str, channel_id: str):
        conn = await self.connect()
        cursor = await conn.execute('''
            SELECT setting_name, setting_value FROM channel_settings WHERE guild_id = ? AND channel_id = ?
        ''', (guild_id, channel_id))
        rows = await cursor.fetchall()
        await conn.close()
        return {row[0]: row[1] for row in rows} if rows else {}
    async def insert_chat_history(self, message, client = None):
        conn = await self.connect()
        try:
            if isinstance(message, Message):
                # Ensure client is provided for Message type
                assert client is not None, "Client must be provided for Message type"
                row = MessageInfo(message, client)
                await conn.execute('''
                    INSERT INTO chat_history (guild_id, guild_name, channel_id, channel_name, author_id, author_name, message)
                    VALUES (:guild_id, :guild_name, :channel_id, :channel_name, :author_id, :author_name, :message)
                ''', row)
                await conn.commit()
                logging.info(f"[Async] Inserted chat history for message from {row['author_name']} in {row['channel_name']}")
            elif isinstance(message, dict):
                row = message
                await conn.execute('''
                    INSERT INTO chat_history (guild_id, guild_name, channel_id, channel_name, author_id, author_name, message)
                    VALUES (:guild_id, :guild_name, :channel_id, :channel_name, :author_id, :author_name, :message)
                ''', row)
                await conn.commit()
                logging.info(f"[Async] Inserted chat history for message from {row['author_name']} in {row['channel_name']}")
        finally:
            await conn.close()
    async def fetch_chat_history(self, guild_id: str, channel_id: str, limit: int = 14):
        conn = await self.connect()
        try:
            cursor = await conn.execute('''
            with tbl as (
                SELECT created_at FROM chat_history
                WHERE guild_id = ? AND channel_id = ? 
                and author_id != 'tool_call' and author_name = 'Fefe'
                ORDER BY created_at desc
                LIMIT ?
            )
            SELECT message FROM chat_history
            WHERE guild_id = ? AND channel_id = ?
            AND created_at <= (SELECT min(created_at) FROM tbl)
            ORDER BY created_at
            ''', (guild_id, channel_id, limit, guild_id, channel_id))
            rows = await cursor.fetchall()
            messages = [eval(row[0]) for row in rows]
        except: 
            logging.error(f"[Async] Error fetching chat history for guild_id: {guild_id}, channel_id: {channel_id}")
            messages = []
        finally:
            await conn.close()
        return messages

db = DatabaseConnector(initialize=True)