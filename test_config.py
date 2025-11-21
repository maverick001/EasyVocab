import os
from config import Config

print(f"Current working directory: {os.getcwd()}")
print(f"GOOGLE_API_KEY from Config: {Config.GOOGLE_API_KEY}")
print(f"GEMINI_MODEL from Config: {Config.GEMINI_MODEL}")
print(f"DB_HOST from Config: {Config.DB_HOST}")

from dotenv import load_dotenv
print("Calling load_dotenv() again...")
load_dotenv()
print(f"GOOGLE_API_KEY from os.environ: {os.environ.get('GOOGLE_API_KEY')}")
