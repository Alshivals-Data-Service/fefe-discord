from fefe import secrets, db
import logging
class Tools():
    def __init__(self):
        self.specs = []
        self.available_tools = {}

        # Add the gif_search function to the specs
        self.specs.append({
            "type": "function",
            "function": {
                "name": "gif_search",
                "description": "Find a GIF to use in your conversation to express emotion using this tool, then send the url to the channel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query used to search for a GIF. e.g. Anime girl wave",
                        }
                    },
                    "required": ["query"],
                },
            }
        })
        self.available_tools['gif_search'] = self.gif_search

        # Add text_message function to the specs
        self.specs.append({
            "type": "function",
            "function": {
                "name": "text_message",
                "description": "Send text messages to the channel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "messages": {
                            "type": "array",
                            "description": "List of messages to send to the channel.",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["messages"],
                },
            }
        })
        self.available_tools['text_message'] = self.text_message

    async def gif_search(self, query):
        import requests
        import json 
        import random
        """
        Search for GIFs using the Tensor API.
        """
        base_url = "https://tenor.googleapis.com/v2/search"
        params = {
            'q': 'anime girl '+query,
            'media_format': "gif,",
            'key': secrets.Google['tenor_api_key'],
            'client_key': 'fefe',
            'limit': 20
        }      
        r = requests.get(base_url, params=params)
        # print(r.status_code)
        if r.status_code == 200:
            # load the GIFs using the urls for the smaller GIF sizes
            top_gifs = json.loads(r.content)
            top_gifs = [{'url': x['media_formats']['gif']['url'], 'tags': x['tags'][:5]} for x in top_gifs['results']]
            return top_gifs
        else:
            # handle the error
            logging.error(f"Error: {r.status_code} - {r.text}")
            return []
        
    async def text_message(self, message, messages):
        for text in messages:
            await message.channel.send(text)



tools = Tools()