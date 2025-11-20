
from app import get_db_connection, init_db_pool
import requests
import time

def verify_review_increment():
    print("Initializing database pool...")
    init_db_pool()
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Get a word to test
        print("Fetching a word to test...")
        cursor.execute("SELECT id, word, review_count FROM words LIMIT 1")
        word = cursor.fetchone()
        
        if not word:
            print("❌ No words found in database to test.")
            return

        word_id = word['id']
        initial_count = word['review_count']
        print(f"Testing with word: '{word['word']}' (ID: {word_id})")
        print(f"Initial review count: {initial_count}")
        
        conn.close() # Close connection to ensure no open transaction holding old snapshot
        
        # 2. Call the API to increment (simulate button click)
        print("Sending review request to API...")
        try:
            response = requests.post(f"http://localhost:5000/api/words/{word_id}/review")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Response: Success. New count returned: {data.get('review_count')}")
            else:
                print(f"❌ API Request Failed: {response.status_code} - {response.text}")
                return
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to server. Is it running?")
            return

        # 3. Verify in database directly (New Connection)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT review_count FROM words WHERE id = %s", (word_id,))
        updated_word = cursor.fetchone()
        new_count = updated_word['review_count']
        
        print(f"Database review count: {new_count}")
        
        if new_count > initial_count:
            print("✅ SUCCESS: Review count incremented correctly!")
        else:
            print(f"❌ FAILURE: Count did not increment. Expected > {initial_count}, got {new_count}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    verify_review_increment()
