import fefe.guilds 
from fefe.guilds.Db import GuildDB
import discord
import logging
from datetime import datetime, timezone

class SENSITIVE(Exception):
    def __init__(self):
        self.message = "This setting is sensitive and cannot be fetched."
        super().__init__(self.message)
    def __str__(self):
        return self.message

class GuildSetting(GuildDB):
    def __init__(self, guild: discord.Guild, setting_name: str, setting_value=None, set_by='system', modified_timestamp=datetime.now().astimezone(timezone.utc)):
        super().__init__(guild)
        self.guild = guild
        self.setting_name = setting_name
        self.setting_value = setting_value
        self.set_by = set_by
        self.modified_timestamp = modified_timestamp  # Use current time if not provided  
    # update pushes to database. To phase out the old update method
    async def stash(self):
        conn = await self.connect()
        await conn.execute("""
        INSERT INTO guild_settings (guild_id, setting_name, setting_value, set_by, modified_timestamp)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(guild_id, setting_name) DO UPDATE SET 
            setting_value = excluded.setting_value,
            set_by = excluded.set_by,
            modified_timestamp = excluded.modified_timestamp
        """, (self.guild.id, self.setting_name, self.setting_value, self.set_by, self.modified_timestamp))
        
        await conn.commit()
        logging.info(f"Updated guild_settings for {self.guild.id} - {self.setting_name}: {self.setting_value}")
        await conn.close()
    def stash_sync(self):
        """
        Synchronous update method to push the setting to the database.
        """
        conn = self.connect_sync()
        conn.execute("""
        INSERT INTO guild_settings (guild_id, setting_name, setting_value, set_by, modified_timestamp)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(guild_id, setting_name) DO UPDATE SET 
            setting_value = excluded.setting_value,
            set_by = excluded.set_by,
            modified_timestamp = excluded.modified_timestamp
        """, (self.guild.id, self.setting_name, self.setting_value, self.set_by, self.modified_timestamp))
        
        conn.commit()
        logging.info(f"Updated guild_settings for {self.guild.id} - {self.setting_name}: {self.setting_value}")
        conn.close()

class GuildSettings(GuildDB):
    def __init__(self, guild: discord.Guild):
        super().__init__(guild)
    def fetch_all(self):
        """
        Fetch all settings for the guild from the database.
        Returns a dictionary of setting_name to GuildSetting objects.
        """
        conn = self.connect_sync()
        cursor = conn.execute("SELECT setting_name, setting_value, set_by, modified_timestamp FROM guild_settings WHERE guild_id = ?", (self.guild.id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        all_settings = {}
        if rows:
            for row in rows:
                setting_name, setting_value, set_by, modified_timestamp = row
                all_settings[setting_name] = GuildSetting(self.guild, setting_name, setting_value, set_by, modified_timestamp)
            return all_settings
        return {}
    def fetch_sync(self, setting_name, sensitive_check=False):
        # if key or secret in setting_name, return None
        if sensitive_check:  # This is to check if the setting is sensitive
            if setting_name in ['api_key', 'spotify_client_id', 'spotify_client_secret']:
                raise SENSITIVE()
        """
        Fetch a specific setting for the guild from the database.
        Returns a GuildSetting object or None if not found.
        """
        conn = self.connect_sync()
        cursor = conn.execute("SELECT setting_value, set_by, modified_timestamp FROM guild_settings WHERE guild_id = ? AND setting_name = ?", (self.guild.id, setting_name))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            setting_value, set_by, modified_timestamp = row
            return GuildSetting(self.guild, setting_name, setting_value, set_by, modified_timestamp)
        return GuildSetting(self.guild, setting_name, None, None, None)  # Return an empty GuildSetting if not found
    async def fetch(self, setting_name, sensitive_check=False):
        if sensitive_check:  # This is to check if the setting is sensitive
            if setting_name in ['api_key', 'spotify_client_id', 'spotify_client_secret']:
                raise SENSITIVE()
        """
        Fetch a specific setting for the guild from the database.
        """
        conn = await self.connect()
        cursor = await conn.execute("SELECT setting_value, set_by, modified_timestamp FROM guild_settings WHERE guild_id = ? AND setting_name = ?", (self.guild.id, setting_name))
        row = await cursor.fetchone()
        await cursor.close()
        await conn.close()
        if row:
            setting_value, set_by, modified_timestamp = row
            return GuildSetting(self.guild, setting_name, setting_value, set_by, modified_timestamp)
        return GuildSetting(self.guild, setting_name, None, None, None)  # Return an empty GuildSetting if not found