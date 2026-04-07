import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load keys from .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

print(f"--- Gemini Local Test ---")
print(f"API Key cleaning: {api_key[:6]}...{api_key[-4:] if len(api_key)>10 else ''}")

if not api_key or "your_gemini" in api_key:
    print("❌ ERROR: No valid API key found in .env file.")
    exit(1)

genai.configure(api_key=api_key)

models_to_test = [
    "models/gemini-1.5-flash",
    "models/gemini-1.5-flash-latest",
    "models/gemini-pro",
]

for model_name in models_to_test:
    print(f"\nTesting model: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello AgriSpark' if you are working.")
        print(f"✅ SUCCESS: {response.text.strip()}")
    except Exception as e:
        print(f"❌ FAILED: {str(e)[:150]}")

print("\n--- Test Finished ---")
