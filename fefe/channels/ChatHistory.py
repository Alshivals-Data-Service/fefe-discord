import discord
import logging
import fefe.guilds 
from fefe.guilds.Db import GuildDB
from fefe.guilds.Guild import Guild
import json

class ChatHistory(GuildDB):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(channel.guild)
        self.channel = channel
    async def fetch(self, limit=14, user_id=None):
        conn = await self.connect()
        cursor = await conn.execute(f"""
            with tbl as (
                SELECT user_id, user_name, created_at, message FROM chat_history 
                WHERE guild_id = ? AND channel_id = ?
                {' AND user_id = ?' if user_id else ''}
                ORDER BY created_at DESC
                LIMIT ?
            )
            SELECT user_id, user_name, created_at, message FROM tbl
            ORDER BY created_at
        """, (self.guild.id, self.channel.id, limit))
        rows = await cursor.fetchall()
        await cursor.close()
        await conn.close()
        if rows:
            rows = [{
                'user_id': row[0],
                'user_name': row[1],
                'created_at': row[2],
                'message': eval(row[3])
            } for row in rows]            

            return rows
        return []
    async def stash(self, JSON):
        try:
            """
            Save the message to the database.
            """
            conn = await self.connect()
            cursor = await conn.cursor()
            # Insert the message into the chat_history table
            await cursor.execute('''
                INSERT INTO chat_history (guild_id, guild_name, channel_id, channel_name, user_id, user_name, created_at, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                JSON['guild_id'],
                JSON['guild_name'],
                JSON['channel_id'],
                JSON['channel_name'],
                JSON['user_id'],
                JSON['user_name'],
                JSON['created_at'],
                json.dumps(JSON['message']) if isinstance(JSON['message'], (dict, list)) else JSON['message']  # Ensure message is JSON serializable
            ))
            await conn.commit()
            await cursor.close()
            await conn.close()
            return True
        except Exception as e:
            logging.error(f"Error stashing message: {e}")

