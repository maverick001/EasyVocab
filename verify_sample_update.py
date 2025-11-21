import requests
import mysql.connector
from config import Config
import random
import string
import time

def get_word_info(word_id):
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, word, review_count, sample_sentence FROM words WHERE id = %s", (word_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def test_sample_sentence_increment():
    print("Starting verification...")
    
    # 1. Create a test word
    random_suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
    word_text = f"test_sample_{random_suffix}"
    
    payload = {
        "word": word_text,
        "translation": "test_translation",
        "category": "AI",
        "sample_sentence": "Initial sentence"
    }
    
    try:
        response = requests.post('http://localhost:5000/api/words', json=payload)
        if response.status_code != 200:
            print(f"❌ Failed to create test word: {response.text}")
            return
        
        word_id = response.json()['word_id']
        print(f"Created test word: {word_text} (ID: {word_id})")
        
        # Initial check
        info = get_word_info(word_id)
        initial_count = info['review_count']
        print(f"Initial review count: {initial_count}")
        
        # 2. Update sample sentence (should increment)
        print("\nTest 1: Updating sample sentence...")
        update_payload = {
            "sample_sentence": "Updated sentence"
        }
        requests.put(f'http://localhost:5000/api/words/{word_id}', json=update_payload)
        
        info = get_word_info(word_id)
        count_after_update = info['review_count']
        print(f"Count after sample update: {count_after_update}")
        
        if count_after_update == initial_count + 1:
            print("✅ SUCCESS: Count incremented on sample update")
        else:
            print(f"❌ FAILURE: Count did not increment. Expected {initial_count + 1}, got {count_after_update}")

        # 3. Update translation only (should NOT increment)
        print("\nTest 2: Updating translation only...")
        update_payload_trans = {
            "translation": "Updated translation"
        }
        requests.put(f'http://localhost:5000/api/words/{word_id}', json=update_payload_trans)
        
        info = get_word_info(word_id)
        count_after_trans = info['review_count']
        print(f"Count after translation update: {count_after_trans}")
        
        if count_after_trans == count_after_update:
            print("✅ SUCCESS: Count did NOT increment on translation update")
        else:
            print(f"❌ FAILURE: Count incremented incorrectly. Expected {count_after_update}, got {count_after_trans}")

        # 4. Update sample sentence to same value (should NOT increment)
        print("\nTest 3: Updating sample sentence to SAME value...")
        update_payload_same = {
            "sample_sentence": "Updated sentence"
        }
        requests.put(f'http://localhost:5000/api/words/{word_id}', json=update_payload_same)
        
        info = get_word_info(word_id)
        count_after_same = info['review_count']
        print(f"Count after same sample update: {count_after_same}")
        
        if count_after_same == count_after_trans:
            print("✅ SUCCESS: Count did NOT increment on same sample update")
        else:
            print(f"❌ FAILURE: Count incremented incorrectly. Expected {count_after_trans}, got {count_after_same}")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running?")
        return

if __name__ == "__main__":
    test_sample_sentence_increment()
