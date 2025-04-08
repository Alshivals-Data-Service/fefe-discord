import logging
import json
from fefe.Message import FefeMessage
from fefe.tools import PyXecutor
from fefe.tools import gif_search
from fefe.tools import Google
# Function to handle tool calls. 
from openai.types.chat import ChatCompletionMessage
class tool_handler:
    def __init__(self):
        self.available_tools = []
        self.available_functions = {}
        self.initialize()
    def initialize(self):
        #########################################
        # Gif Search Tool
        self.available_tools.append(gif_search.spec)
        self.available_functions['gif_search'] = gif_search.gif_search

        #########################################
        # PyXecutor Tool (run_python)
        self.available_tools.append(PyXecutor.spec)

        ##########################################
        # GoogleCalendar
        self.available_tools.append(Google.spec)

    async def handler(self, message: FefeMessage, response: ChatCompletionMessage):
        """
        Handle tool calls in an OpenAI ChatCompletionMessage object
        """
        tool_calls = response.tool_calls
        tool_call_responses = []
        if not tool_calls:
            return None
        else:
            # Handle each tool call in the message
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                function_to_call = self.available_functions.get(tool_name, None)
                function_args = json.loads(tool_call.function.arguments)
                
                # Handle gif_search calls
                if tool_name == 'gif_search':
                    tool_responses = await function_to_call(tool_call.id, **function_args)
                    tool_call_responses.append(tool_responses)

                if tool_name == 'run_python':
                    pyxecutor = PyXecutor.PyXecutor(message) # Will run from user's directory within the guild data directory
                    tool_call_responses = await pyxecutor.execute(function_args['code'], tool_call.id)
                    await pyxecutor.send_files()

                if tool_name == 'calendar_events':
                    # Fetch the user's google calendar object
                    calendar = Google.GoogleCalendar(message)
                    if not calendar.credentials:
                        await calendar.authenticate()
                    tool_call_responses = calendar.get_events(tool_call_id=tool_call.id)
            logging.debug(f"Tool call responses: {tool_call_responses}")
            return tool_call_responses
        
    