import discord 
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from discord.ext import commands, tasks
from discord import app_commands
import fefe
from fefe.Message import FefeMessage
import fefe.guilds
from fefe.guilds.Settings import SENSITIVE
import enum
import logging

# Set logging level to info
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot_token = fefe.secrets.Discord["bot_token"]

intents = discord.Intents.all()  # Enables all intents for the bot

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        self.tree = app_commands.CommandTree(self)

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        # This copies the global commands over to all guilds the bot is in.
        # This is useful for testing commands that are not yet ready for global use.
        # await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))  # Uncomment this line to sync commands to a specific guild
        await self.tree.sync()

client = MyClient(intents=intents)

@client.event 
async def on_ready():
    logging.info(f'Logged in as {client.user.name} - {client.user.id}') 
    
    
    # You can add any additional setup here, like syncing commands or checking server status
@client.event
async def on_message(message):
    logging.info(f"Message from {message.author.name} ({message.author.id}): {message.content}")  # Log the message content
    logging.info(f"Attachments: {message.attachments}")  # Log the attachments
    for attachment in message.attachments:
        logging.info(f"Attachment URL: {attachment.url}")
    message = FefeMessage(message, client) # Create a FefeMessage object to handle the message
    # Test store the message in the database
    await message.stash()

    # This prevents the bot from responding to its own messages
    if message.author == client.user:
        return

    # Get the model for the guild 
    model = fefe.Model(message)  # Create a model for the guild
    # Get a response from the model 
    response = await model.reply(message)  # Get the response from the model
    if response:
        # Send the response back to the channel
        await message.channel.send(response)  # Send the response to the channel. It will be recorded by the on_message event

@client.tree.command(name="settings", description="View or change Fefe's settings.")
@app_commands.describe(setting="The setting to view or change", value="The new value for the setting")
@app_commands.choices(
    setting = [
        app_commands.Choice(name="api_key", value="api_key"),
        app_commands.Choice(name="model", value="model"),
        app_commands.Choice(name="personality", value="personality"),
        app_commands.Choice(name="spotify_client_id", value="spotify_client_id"),
        app_commands.Choice(name="spotify_client_secret", value="spotify_client_secret"),
    ])
@app_commands.checks.has_permissions(administrator=True)  # Only allow administrators to use this command
async def settings(interaction: discord.Interaction, setting: str, value: str = None):
    await interaction.response.defer(thinking=True)
    # Fetch current setting object from the database
    guild = fefe.Guild(interaction.guild)

    if value:
        try:
            setting_obj = await guild.settings.fetch(setting, sensitive_check=False)
        except SENSITIVE as e:
            # If the setting is sensitive, we don't want to expose it
            await interaction.followup.send(f"{setting} is set but cannot be modified.")
            logging.debug(f"Sensitive setting for {interaction.guild.name}: {setting}. This is a bug and should be reported.")
            return

        # If a value is provided, update the setting in the database
        setting_obj.setting_value = value
        setting_obj.set_by = interaction.user.id
        await setting_obj.stash()
        # Note: setting_obj.modified_timestamp is a string in the format "YYYY-MM-DD HH:MM:SS" in UTC
        dt = datetime.now(timezone.utc)
        dt = int(dt.timestamp())
        # dt is 
        discord_timestamp = f"<t:{dt}:R>"
        await interaction.followup.send(f"{setting_obj.setting_name} updated by {interaction.user.name} {discord_timestamp}")
    else:
        # If no value is provided, assuming they want to view the current setting
        try:
            setting_obj = await guild.settings.fetch(setting, sensitive_check=True)  # Fetch the current setting object from the database
            await interaction.followup.send(f"{setting_obj.setting_name} updated by {setting_obj.set_by}")
        except SENSITIVE as e:
            # If the setting is sensitive, we don't want to expose it
            await interaction.followup.send(f"{setting} is set but cannot be displayed.")
            return
        except Exception as e:
            # Handle any other exceptions that may arise
            await interaction.followup.send(f"Error fetching setting: {e}")
            logging.error(f"Error fetching {setting} for {interaction.guild.name}: {e}")
            return

# @client.tree.command(name="guild_settings", description="View or change Fefe's settings.")
# @app_commands.describe(setting="The setting to view or change", value="The new value for the setting")
# @app_commands.choices(
#     setting = [
#         app_commands.Choice(name="personality", value="personality"),
#     ])
# @commands.has_permissions(administrator=True)  # Only allow administrators to use this command
# async def GuildSettings(interaction: discord.Interaction, setting: str, value: str = None):
#     # Fetch current setting object from the database 
#     setting = await fefe.settings.GuildSettings.fetch(interaction.guild.id, setting)
#     if value is None:
#         # If no value is provided, assuming they want to view the current setting
#         await interaction.response.send_message(f"Current setting for {setting.setting_name}: {setting.setting_value} (set by {setting.set_by} on {setting.modified_timestamp})")
#     else:
#         # If a value is provided, update the setting in the database
#         setting.setting_value = value
#         setting.set_by = interaction.user.id  # Set the user who changed the setting
#         await setting.update()  # Update the setting in the database
#         await interaction.response.send_message(f"Setting {setting.setting_name} updated to {setting.setting_value} by {interaction.user.name}")

# Since our bot is an administrator, they keep track of when members join and leave a guild.
@client.event
async def on_guild_join(guild):
    logging.info(f"Joined guild: {guild.name} (ID: {guild.id})")
    # You can initialize settings for the guild here if needed
@client.event
async def on_guild_remove(guild):
    logging.info(f"Left guild: {guild.name} (ID: {guild.id})")
    # You can clean up settings for the guild here if needed

client.run(bot_token) 