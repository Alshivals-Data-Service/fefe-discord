import discord
from datetime import datetime, timezone
from discord import Interaction
from discord.message import Message
from discord.ext.commands import Context
import fefe.guilds 
from fefe.guilds.Db import GuildDB
from fefe.guilds.Settings import GuildSettings

class Guild:
    def __init__(self, discord_guild: discord.Guild):
        self.id = discord_guild.id
        self.discord_guild = discord_guild 
        self.db = GuildDB(discord_guild)
        self.settings = GuildSettings(discord_guild)
        self.guild = discord_guild

    def connect_sync(self):
        """
        Connect to the SQLite database synchronously.
        """
        return self.db.connect_sync()
    async def connect(self):
        """
        Connect to the SQLite database asynchronously.
        """
        return await self.db.connect()
