import json
import os
import logging
import discord 
from discord import Message, Interaction
from discord.ext.commands import Context
import fefe.guilds
from fefe.guilds.Guild import Guild
import fefe.channels
from fefe.channels.TextChannel import TextChannel
from datetime import datetime

class FefeMessage(Guild):
    def __init__(
            self, 
            message: discord.Message, 
            client: discord.Client
            ):
        super().__init__(message.guild)
        self.json = {
            'guild_id': None,
            'guild_name': None,
            'channel_id': None,
            'channel_name': None,
            'user_id': None,
            'user_name': None,
            'created_at': datetime.now(),
            'message': {}
        }
        self.message = message
        self.guild = Guild(message.guild)
        if isinstance(self.message.channel, discord.TextChannel):
            self.channel = TextChannel(self.message.channel)
        else:
            raise ValueError("Channel type not yet supported. Please switch to a text channel.")

        self.guild_dir = self.guild.db.guild_dir
        if not os.path.exists(self.guild_dir):
            os.makedirs(self.guild_dir)
        self.user_dir = os.path.join(self.guild_dir, str(message.author.id))
        if not os.path.exists(self.user_dir):
            os.makedirs(self.user_dir)
        
        self.author = message.author
        self.client = client

        if isinstance(self.message, (Context, Message)):
            role = "assistant" if message.author == client.user else "user"
            message_obj = {"role": role, "content": [] }
            if self.message.content:
                message_obj['content'].append({"type":"text","text": self.message.content})
            if self.message.attachments:
                for attachment in self.message.attachments:
                    # Check if the attachment is an image
                    if not attachment.url.endswith(('.png', '.jpg', '.jpeg')):
                        continue
                    attachment_url = attachment.url
                    message_obj['content'].append({"type":"image_url","image_url": {"url": attachment_url}})
            self.json = {
                    'guild_id': self.message.guild.id,
                    'guild_name': self.message.guild.name,
                    'channel_id': self.message.channel.id,
                    'channel_name': self.message.channel.name,
                    'user_id': self.message.author.id,
                    'user_name': self.message.author.name,
                    'created_at': self.message.created_at,
                    'message': message_obj
                }
        elif isinstance(self.message, Interaction):
            role = "assistant" if message.user == client.user else "user"
            message_obj = {"role": role, "content": [] }
            if self.message.attachments:
                for attachment in self.message.attachments:
                    # Check if the attachment is an image
                    if not attachment.url.endswith(('.png', '.jpg', '.jpeg')):
                        continue
                    attachment_url = attachment.url
                    message_obj['content'].append({"type":"image_url","image_url": {"url": attachment_url}})
            if self.message.content:
                message_obj['content'].append({"type":"text","text": self.message.content})
            self.json = {
                    'guild_id': self.message.guild.id,
                    'guild_name': self.message.guild.name,
                    'channel_id': self.message.channel.id,
                    'channel_name': self.message.channel.name,
                    'user_id': self.message.user.id,
                    'user_name': self.message.user.name,
                    'created_at': self.message.created_at,
                    'message': message_obj
                }
    async def stash(self):
        await self.channel.ChatHistory.stash(self.json)