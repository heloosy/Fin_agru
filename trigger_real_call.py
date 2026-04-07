import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SID = os.getenv("TWILIO_ACCOUNT_SID")
TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM = os.getenv("TWILIO_PHONE_NUMBER")
URL = os.getenv("BASE_URL")

if URL and URL.endswith("/"):
    URL = URL[:-1]

def main():
    print("\n--- AgriSpark 2.0 Real-Time Call Trigger ---")
    
    if not SID or "xxx" in SID:
        print("❌ Error: TWILIO_ACCOUNT_SID is missing or not configured in .env.")
        return
    if not TOKEN or "your_auth_token" in TOKEN:
        print("❌ Error: TWILIO_AUTH_TOKEN is missing or not configured in .env.")
        return
    if not FROM or "+1xxxxxxxxxx" in FROM:
        print("❌ Error: TWILIO_PHONE_NUMBER is not configured in .env.")
        return
    if not URL or "your-ngrok" in URL:
        print("❌ Error: BASE_URL is not configured (should be your Railway URL).")
        return

    to_number = input("📞 Enter the phone number to call (e.g., +919495327825): ").strip()
    
    if not to_number.startswith("+"):
        print("❌ Error: Phone number must start with '+' and include country code.")
        return

    print(f"\n🚀 Initiating outbound call...")
    print(f"   From: {FROM}")
    print(f"   To:   {to_number}")
    print(f"   URL:  {URL}/ivr/welcome")

    try:
        client = Client(SID, TOKEN)
        call = client.calls.create(
            to=to_number,
            from_=FROM,
            url=f"{URL}/ivr/welcome"
        )
        print(f"\n✅ SUCCESS!")
        print(f"   Call SID: {call.sid}")
        print(f"   Status:   {call.status}")
        print("\nYour phone should ring in a few seconds. Pick it up to interact with the IVR.")
    except Exception as e:
        print(f"\n❌ TWILIO ERROR: {e}")

if __name__ == "__main__":
    main()
