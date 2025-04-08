from openai import OpenAI
from fefe.Secrets import secrets 
from fefe.tools import tools
from fefe.database import db
from discord.message import Message
from discord.client import Client
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function
import json
import logging 

class FefeClient:
    def __init__(self, discord_client: Client = None, model='gpt-4o-mini'):
        self.model = model

    def get_client(self):
        api_key = secrets.OpenAi["api_key"]
        project = secrets.OpenAi.get("project", None)
        organization = secrets.OpenAi.get("organization", None)
        params = {
            "api_key": api_key,
            "project": project,
            "organization": organization
        }
        client = OpenAI(**params)
        return client
    def chat_completion(self, messages):
        # Message must be list or string
        assert isinstance(messages, (list, str)), "Messages must be a list or string"
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        
        elif not all((isinstance(m, dict) and "role" in m and "content" in m) or (isinstance(m, ChatCompletionMessage)) for m in messages):
            raise ValueError("Each message must be a dict with 'role' and 'content' keys")
        client = self.get_client()
        completion = client.chat.completions.create(
            model = self.model,
            messages = messages, 
            tools = tools.specs
        )
        return completion   
    
    async def response(self, message, client):
        """
        Get the full response from the chat completion.
        """
        #print(f"Processing message: {message.content}")
        messages = await db.fetch_chat_history_async(
            guild_id = message.guild.id, 
            channel_id = message.channel.id, 
            limit = 10  # Fetch the last 10 messages for context
        )  # Ideally, there would be a token check in `fetch_chat_history_async`
        personality = await db.get_setting('personality')
        self.instructions = f"""
            {personality}

            You must use the `text_message` tool to send any messages to King Samuel.
            The `text_message` tool allows you to reply to messages in the channel. List your responses in the `messages` parameter. 
            The `gif_search` tool allows you to find a GIF to use in your conversation to express emotion.
            Once you receive a response from the `gif_search` tool call, use the `text_message` tool to send the GIF URL to the channel, along with any other text messages you'd like to send. 
            """
        # Add the instructions to the beginning of the messages
        messages.insert(0, {"role": "developer", "content": self.instructions})
        #print(f"Fetched messages for context: {messages}")
        try: 
            completion = self.chat_completion(messages)

            response = completion.choices[0].message
            if response.tool_calls:
                # Insert a record of the assistant's response into the database
                row = {
                    'guild_id': message.guild.id,
                    'guild_name': message.guild.name,
                    'channel_id': message.channel.id,
                    'channel_name': message.channel.name,
                    'author_id': client.user.id,
                    'author_name': client.user.name,
                    'message': str(response)
                }
                await db.insert_chat_history(row)
                print(f"Inserted assistant response into database: {row}")
                # Handle any tool calls in the response
                await self.handle_tool_calls(message, response)
                # Recurse to handle tool calls
                response = await self.response(message, client)  
            # Return the response to the original message
            return response

        except Exception as e:
            logging.error(f"Error in chat completion: {e}")
            return None
    
    async def handle_tool_calls(self, message, response):
        tool_calls = response.tool_calls
        if not tool_calls:
            return response
        else:
            print("Handling tool calls...")
            for tool_call in tool_calls:
                tool_call_id = tool_call.id
                tool_name = tool_call.function.name
                if tool_name not in tools.available_tools:
                    raise ValueError(f"Tool {tool_name} is not available.")
                tool_to_call = tools.available_tools.get(tool_name,None)
                tool_args = json.loads(tool_call.function.arguments)
                print(f"Calling tool: {tool_name} with args: {tool_args}")
                
                if tool_to_call is None:
                    logging.error(f"Tool {tool_name} not found in available tools.")
                    continue

                if tool_name == 'gif_search':
                    tool_response = await tool_to_call(**tool_args)
                    tool_call_record = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_response)
                    }

                    tool_row = {
                        'guild_id': message.guild.id,
                        'guild_name': message.guild.name,
                        'channel_id': message.channel.id,
                        'channel_name': message.channel.name,
                        'author_id': 'tool_call',
                        'author_name': tool_name,
                        'message': str(tool_call_record)
                    }

                    await db.insert_chat_history(tool_row)
                elif tool_name == 'text_message':
                    tool_call_record = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_args['messages'])
                    }
                    tool_row = {
                        'guild_id': message.guild.id,
                        'guild_name': message.guild.name,
                        'channel_id': message.channel.id,
                        'channel_name': message.channel.name,
                        'author_id': 'tool_call',
                        'author_name': tool_name,
                        'message': str(tool_call_record)
                    }
                    await db.insert_chat_history(tool_row)
                    tool_response = await tool_to_call(message=message, messages=tool_args['messages'])

    
model = FefeClient()

########################################################
# Moderation
########################################################
class Moderation:
    def __init__(self, openai_model='gpt-4o-mini'):
        self.model = openai_model
    def scan(self, message):
        if isinstance(message, Message):
            moderation = model.get_client().moderations.create(input=message.content)
        elif isinstance(message, str):
            moderation = model.get_client().moderations.create(input=message)
        else:
            raise TypeError("Unsupported message type. Expected Message or str.")
        if moderation.results[0].flagged:
            return [u for u, v in moderation.results[0].categories if v]
        return None
moderation = Moderation()