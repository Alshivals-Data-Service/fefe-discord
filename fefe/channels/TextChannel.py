import discord 
import fefe.channels 
from fefe.channels.ChatHistory import ChatHistory
from fefe.guilds.Db import GuildDB
from fefe.guilds.Guild import Guild
class TextChannel(GuildDB):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(channel.guild)
        self.channel = channel
        self.guild = Guild(channel.guild)
        self.id = channel.id
        self.ChatHistory = ChatHistory(channel)
    async def send(self, *args, **kwargs):
        """
        Send a message to the text channel.
        """
        return await self.channel.send(*args, **kwargs)
    