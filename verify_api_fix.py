import requests
import time
import sys


def verify_api():
    url = "http://localhost:5001/api/words/8645"
    print(f"Checking {url}...")

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                word = data["word"]
                print("Word data keys found:", list(word.keys()))

                required_fields = ["image_file", "created_at", "updated_at"]
                missing = [f for f in required_fields if f not in word]

                if not missing:
                    print("✅ SUCCESS: All required fields found!")
                    return True
                else:
                    print(f"❌ FAILURE: Missing fields: {missing}")
                    return False
            else:
                print(f"❌ API Error: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


if __name__ == "__main__":
    # Wait for server to start
    print("Waiting for server...")
    time.sleep(5)

    if verify_api():
        sys.exit(0)
    else:
        sys.exit(1)
