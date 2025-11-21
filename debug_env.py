import os
from dotenv import load_dotenv

print(f"Current working directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")

load_dotenv()
key = os.environ.get('GOOGLE_API_KEY')
print(f"GOOGLE_API_KEY: {key}")
if key:
    print(f"Key length: {len(key)}")
else:
    print("Key is None")
