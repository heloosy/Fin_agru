import requests
import json

def test_whatsapp():
    url = "http://localhost:5000/whatsapp"
    data = {
        "Body": "Hello AgriSpark! My paddy leaves are yellow.",
        "From": "whatsapp:+123456789"
    }
    
    print(f"📡 Sending test to {url}...")
    try:
        response = requests.post(url, data=data, timeout=30)
        print(f"✅ Status Code: {response.status_code}")
        print(f"💬 Bot Reply:\n{response.text}")
    except Exception as e:
        print(f"❌ Failed to reach bot: {str(e)}")

if __name__ == "__main__":
    test_whatsapp()
