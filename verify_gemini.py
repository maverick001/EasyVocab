import requests
import json

def test_gemini_generation():
    print("Starting Gemini verification...")
    
    url = 'http://localhost:5000/api/generate-sample'
    payload = {
        "word": "serendipity"
    }
    
    try:
        print(f"Requesting sample sentence for 'serendipity'...")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ SUCCESS: Gemini generated a sentence:")
                print(f"   \"{result.get('sentence')}\"")
            else:
                print(f"❌ FAILURE: API returned success=False")
                print(f"   Error: {result.get('error')}")
        else:
            print(f"❌ FAILURE: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running?")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_gemini_generation()
