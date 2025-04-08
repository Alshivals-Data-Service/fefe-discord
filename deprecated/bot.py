import discord 
from discord.ext import commands, tasks
from discord import app_commands
import fefe
import enum
import logging

# Set logging level to info
logging.basicConfig(level=logging.INFO)

bot_token = fefe.Secrets.Discord["bot_token"]

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
    logging.info('------')
    print("Testing...")
    test = await fefe.db.guild_settings()
    print(f'\nGuild setting: {test}\n')  # Log the test setting for debugging
    # You can add any additional setup here, like syncing commands or checking server status
@client.event
async def on_message(message):

    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Pass through moderation
    moderation_test = fefe.moderation.scan(message)

    await fefe.db.insert_chat_history(message, client)  # Insert message into the database


    if moderation_test:
        await message.channel.send(f"Message flagged for category: {', '.join(moderation_test)}")
        return
    
    final_response = await fefe.model.response(message, client)
    if final_response:
        await message.channel.send(final_response.content)
    # messages = await fefe.db.fetch_chat_history_async(
    #     guild_id = message.guild.id, 
    #     channel_id = message.channel.id, 
    #     limit = 10  # Fetch the last 10 messages for context
    # ) # Ideally, there would be a token check in `fetch_chat_history_async`
    
    # # Print what is in the database
    # test = await fefe.db.fetch_chat_history_async(guild_id = message.guild.id, channel_id = message.channel.id)
    # print(test)  # Print the chat history for debugging

# Slash command for Viewing/Changing Fefe's settings
@client.tree.command(name="settings", description="View or change Fefe's settings.")
@app_commands.describe(setting="The setting to view or change", value="The new value for the setting")
@app_commands.choices(
    setting = [
        app_commands.Choice(name="personality", value="personality"),
        app_commands.Choice(name="instructions", value="instructions"),
        app_commands.Choice(name="model", value="model"),
        app_commands.Choice(name="response_mode", value="response_mode"),
    ]
    )
@commands.has_permissions(administrator=True)  # Only allow administrators to use this command
async def Settings(interaction: discord.Interaction, setting: str, value: str = None):
    """
    View or change Fefe's settings.
    """
    if value is None:
        await interaction.response.send_message(f"Current value for {setting}: {current_value}")
    else:
        # Update the setting with the new value
        await interaction.response.send_message(f"Updated {setting} to {value}")

client.run(bot_token) 