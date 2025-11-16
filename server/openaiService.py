import os
from dotenv import load_dotenv
from openai import OpenAI


class OpenAIService:
    """
    A service class to handle all interactions with the OpenAI API.
    It automatically loads the API key from the .env file.
    """
    def __init__(self):
        # 1. Load the environment variables from the .env file.
        # This MUST be called before the OpenAI client is initialized 
        # so the environment variable is available.
        load_dotenv()
        
        # 2. Initialize the OpenAI client.
        # It automatically finds and uses the OPENAI_API_KEY 
        # from the environment variables loaded above.
        try:
            self.client = OpenAI()
        except Exception as e:
            # Add a clear error message if the key is missing or invalid
            if "API key" in str(e):
                 print("ERROR: OpenAI API Key not found. Please ensure OPENAI_API_KEY is set in your .env file.")
            raise e

    



