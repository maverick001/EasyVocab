import os
from dotenv import load_dotenv
import mysql.connector

# 1. Force load .env
print("--- Loading .env ---")
load_dotenv()

# 2. Print what we found
print(f"DB_HOST: '{os.environ.get('DB_HOST')}'")
print(f"DB_PORT: '{os.environ.get('DB_PORT')}'")
print(f"DB_USER: '{os.environ.get('DB_USER')}'")

# 3. Try Raw Connection
print("\n--- Testing Connection ---")
try:
    conn = mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME')
    )
    print("SUCCESS! Connected to database.")
    conn.close()
except Exception as e:
    print(f"FAILURE: {e}")
