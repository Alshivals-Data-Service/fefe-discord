from openai import OpenAI
import tiktoken
import discord 
import logging
import fefe.guilds 
from fefe.guilds.Guild import Guild
from fefe.Message import FefeMessage
import fefe.tools
import json

class NOKEY(Exception):
    def __init__(self, guild_id=None, message="API key is not set for this guild. Please set it using `/settings api_key <VALUE>`."):
        self.guild_id = guild_id
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        if self.guild_id:
            return f'{self.message} (Guild ID: {self.guild_id})'
        return self.message

class Model:
    def __init__(self, message: FefeMessage):
        self.message = message # Initiated with the FefeMessage object in order to set guild/person specific settings

    def get_client(self):
        api_key_setting = self.message.guild.settings.fetch_sync('api_key')
        if api_key_setting is None or not api_key_setting.setting_value:
            # Create a special error type for handling this case
            raise NOKEY(guild_id=self.message.guild.id)
        
        params = {
            'api_key': self.message.guild.settings.fetch_sync('api_key').setting_value,
        }
        client = OpenAI(**params)
        return client
    
    async def chat_completion(self, messages, tools=False):
        """
        Get the chat completion from the OpenAI API.
        """
        assert isinstance(messages, (list, str)), "Messages must be a list or string"
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        try:
            client = self.get_client()
        except NOKEY as e:
            logging.debug(f"API key not set for guild {self.message.guild.id}: {e}")
            raise e
        except Exception as e:
            logging.error(f"Error getting OpenAI client: {e}")
            raise e
        if not tools:
            completion = client.chat.completions.create(
                model=self.message.guild.settings.fetch_sync('model').setting_value,
                messages=messages
            )
        else:
            completion = client.chat.completions.create(
                model=self.message.guild.settings.fetch_sync('model').setting_value,
                messages=messages,
                tools=fefe.tools.tool_handler().available_tools
            )
        return completion
    
    async def reply(self, message: FefeMessage):
        """
        Get the full response from the chat completion. 
        """
        # Construct the instructions for the bot.
        logging.debug("=======New message received=======")
        logging.debug(f"Message content: {message.message.content}")
        logging.debug(f"Fetching personality setting for guild {message.guild.id}")
        personality_setting = await message.guild.settings.fetch('personality')
        personality = personality_setting.setting_value
        logging.debug(f"Fetching model setting for guild {message.guild.id}")
        model_setting = await message.guild.settings.fetch('model')
        instructions = f"""
{personality}

You are a friendly and flirty discord bot. Reply to the user. Use the `gif_search` tool call to find a gif to include in your response.
        """
        messages = [{'role': 'system', 'content': instructions}] # Should be changed to `role: developer` in the future

        # Fetch the chat history for the guild
        logging.debug(f"Fetching chat history for guild {message.guild.id}")
        chat_history = await message.channel.ChatHistory.fetch(limit=14)   

        # Add the chat history to the messages
        for chat in chat_history:
            try:
                messages.append(eval(chat['message']))
            except Exception as e:
                logging.error(f"Error parsing chat history message: {e} \nchat['message']: {chat['message']}")
        # Now add the current message to the messages. This is FefeMessage.json

        messages.append(message.json['message'])

        # Now we are ready to get the chat completion
        try:
            logging.debug(f"Getting chat completion for guild {message.guild.id}")
            completion = await self.chat_completion(messages, tools=True)
        except NOKEY as e:
            await message.channel.send(str(e))
            return None
        except Exception as e:
            logging.error(f"Error in chat completion: {e}")
            return None

        # Get the response from the completion
        response = completion.choices[0].message
        logging.debug(f"Chat completion response: {response}")
        # Pass through tool handler
        logging.debug("Handling tool calls in the response")
        tool_handler = fefe.tools.tool_handler()
        tool_call_responses = await tool_handler.handler(message, response)
        logging.debug(f"Tool call responses: {tool_call_responses}")
        # If no tool calls, we are done
        if tool_call_responses:
            # Add the ChatCompletion to the messages for the next round
            messages.append(response)
            # Add the tool call responses to the messages
            for tool_call_response in tool_call_responses:
                messages.append(tool_call_response)
            # Get the last response from the chat completion
            print(f"Getting final response after tool calls. Messages included:")
            for i, msg in enumerate(messages):
                print(f"Message {i}: {msg}")
            response = await self.chat_completion(messages, tools=False)
            response = response.choices[0].message
        
        logging.debug(f"Final response: {response}")
        return response.content