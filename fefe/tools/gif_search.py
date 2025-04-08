from fefe.Secrets import secrets
import json
import logging

spec = {
    "type": "function",
    "function": {
        "name": "gif_search",
        "description": "Search for a GIF using the Tenor API. ",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term for the GIF."
                }
            }
        }
    }
}

async def gif_search(tool_call_id, query, limit=10):
    """
    Search for a GIF using the Tenor API.
    """
    import requests
    import os 
    base_url = "https://tenor.googleapis.com/v2/search"

    params = {
        'q': 'anime girl ' +query, # Experimenting with bot themes.
        "media_format": "gif",
        "key": secrets.get('Google')['tenor_api_key'],
        "limit": limit
    }

    r = requests.get(base_url, params=params)
    if r.status_code == 200:
        top_gifs = json.loads(r.content)
        logging.debug(f"GIF search response: {top_gifs}")
        # We need to give the model a list of GIF URLs so it can choose one.
        if not top_gifs['results']:
            # If no results, return an empty response
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": []
            }
        tool_response = {
            'role': 'tool',
            'tool_call_id': tool_call_id,
            'content': [
                {
                    "type": "text",
                    "text": f"""
GIF: {gif['title']} 
url: {gif['media_formats']['gif']['url']} - {gif['tags'][:5]}
tags: {', '.join(gif['tags'][:5])}
""",
                } for gif in top_gifs['results']
            ]
        }
        return tool_response