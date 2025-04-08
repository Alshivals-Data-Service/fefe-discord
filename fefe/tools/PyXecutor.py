import os
from pathlib import Path
import logging 
import contextlib  
import io
import base64
import re
import discord
import multiprocessing
import asyncio

import fefe.guilds
from fefe.guilds.Db import GuildDB
from fefe.Message import FefeMessage

spec = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": "Execute Python code.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute. Make sure to use triple backticks (```) to format the code block. Include any necessary imports. Do not attempt to display any graphs or images you might generate in the code, e.g. do not use `plt.show()`. Instead, export deliverables to the working directory. The bot will return these to the user for you."
                }
            },
            "required": ["code"]
        }
    }
}

############################
# llm tools
############################
# Use for extracting code from the LLM's responses.
# Written by @alshival circa 2022.
# This will extract code within code blocks from LLM responses. 

class ReturnFile:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.OpenAI_filetype()
        self.filetype()
        self.is_image = self.check_if_image()
        self.name = self.filepath.name
        self.url = None
        self.spec = None
        if not self.filepath.exists():
            raise FileNotFoundError(f"File {self.filepath} does not exist.")
        if self.is_image:
            with open(self.filepath, 'rb') as f:
                encoded_string = base64.b64encode(f.read()).decode('utf-8')
            self.url = f"data:image/{self.openai_filetype};base64,{encoded_string}"
        self.File = discord.File(self.filepath)
        self.Spec()
    def filetype(self):
        filetype_match = re.search(r'\.(\w+)$', str(self.filepath))
        if filetype_match:
            self.filetype = filetype_match.group(1).lower()
        else:
            raise ValueError(f"Could not determine file type for {self.filepath}")
    def OpenAI_filetype(self):
        """
        Return the filetype for OpenAI API.
        """
        if self.filetype in ['jpg', 'jpeg']:
            self.openai_filetype = 'jpeg'
        elif self.filetype in ['png', 'webp']:
            self.openai_filetype = 'png'
        else:
            self.openai_filetype = None
    def check_if_image(self):
        return self.filetype in ['jpg', 'jpeg', 'png', 'webp']
    def Spec(self):
        if self.is_image:
            self.spec = {
                'type': 'output_image',
                'image_url': self.url
            }
        else:
            self.spec = {
                'type': 'output_file',
                'filetype': self.filetype
            }

def _run_code(code_string, exec_dir, queue):
    """
    Helper function to run code in a separate process.
    Changes the working directory to exec_dir, executes the code,
    captures stdout, and puts the result (or error) into the provided queue.
    """
    import os
    import contextlib
    import io
    output_buffer = io.StringIO()
    try:
        os.chdir(exec_dir)
        with contextlib.redirect_stdout(output_buffer):
            local_vars = {}
            exec(code_string, local_vars, local_vars)
        queue.put({'output': output_buffer.getvalue()})
    except Exception as e:
        queue.put({'error': str(e)})
    finally:
        output_buffer.close()

class PyXecutor:
    """
    A class to handle Python code extraction and execution from LLM responses.
    """
    def __init__(self, message: FefeMessage):
        self.message = message 
        # Ensure the user's download directory exists.
        self.exec_dir = Path(self.message.db.guild_dir) / str(message.author.id)
        if not os.path.exists(self.exec_dir):
            os.makedirs(self.exec_dir)
        self.files_to_send = []
        
    def extract_code(self, response_text):
        pattern = r"```(?:[a-z]*\s*)?(.*?)```\s*"
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            extracted_code = match.group(1)
        else:
            return None
        return re.sub(';','', extracted_code)

    async def execute(self, code: str, tool_call_id: str, timeout=100):
        tool_call_response = {
            'role': 'tool',
            'tool_call_id': tool_call_id,
            'content': []  # Here, we add output and files as we construct them.
        }
        code_string = self.extract_code(code)
        if code_string is None:
            code_string = code
        logging.debug(f"Executing code: {code_string}")
        
        # Resolve the execution directory path
        exec_dir_str = str(self.exec_dir.resolve())
        
        # Create a multiprocessing Queue to capture output from the process
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=_run_code, args=(code_string, exec_dir_str, queue))
        process.start()
        
        # Wait for the process to finish with the given timeout using asyncio.to_thread to avoid blocking the event loop.
        await asyncio.to_thread(process.join, timeout)
        if process.is_alive():
            process.terminate()
            process.join()
            result = {'error': 'Execution timed out.'}
        else:
            if not queue.empty():
                result = queue.get()
            else:
                result = {'error': 'No output received.'}
        
        # Reset working directory to the bot's home directory in the main process.
        os.chdir(self.message.db.bot_home_dir)
        
        if 'error' in result:
            logging.error(f"Error executing code: {result['error']}")
            return {
                'role': 'tool',
                'tool_call_id': tool_call_id,
                'content': f"Error: {result['error']}"
            }
        
        output = result.get('output', '')
        if output:
            output_clean = re.sub(r'\s+', ' ', output).strip()
            await self.message.channel.send(f"```python\n{output_clean}```")
            tool_call_response['content'].append({
                'type': 'output_text',
                'text': f'''Code executed:\n####```python\n{code_string}```\n####\nOutput:\n```python\n{output_clean}```'''
            })
        else:
            tool_call_response['content'].append({
                'type': 'output_text',
                'text': f'Code executed:\n####```python\n{code_string}```\n####\nOutput: No output returned.'
            })

        # Collect files to send
        files = os.listdir(self.exec_dir)
        files = [Path(self.exec_dir) / x for x in files if os.path.isfile(Path(self.exec_dir) / x)]

        self.files_to_send = [ReturnFile(x) for x in files if not x.name.startswith('.')]
        for file in self.files_to_send:
            # Rename the file to avoid sending it twice
            new_filepath = file.filepath.parent / f".{file.filepath.name}"
            file.filepath.rename(new_filepath)
            file.filepath = new_filepath
            if file.is_image:
                file_spec = {
                    "type": "output_image",
                    "image_url": file.url
                }
                tool_call_response['content'].append(file_spec)
            else:
                tool_call_response['content'].append({
                    'type': 'output_file',
                    'file': file.filepath
                })
                
        return tool_call_response
    
    async def send_files(self):
        for file in self.files_to_send:
            # Send the file back to the user
            if file.is_image:
                await self.message.channel.send(file=file.File)
            else:
                await self.message.channel.send(file=file.File)
            # Move 'file.type' to '.file.type' to avoid sending the file twice
            new_filepath = file.filepath.parent / f".{file.filepath.name}"
            file.filepath.rename(new_filepath)
            logging.debug(f"Files sent.")
        self.files_to_send = []