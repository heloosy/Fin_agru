import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load keys from .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

print(f"--- Gemini Model Diagnosis ---")
print(f"API Key: {api_key[:6]}...{api_key[-4:] if len(api_key)>10 else ''}")

if not api_key or "your_gemini" in api_key:
    print("❌ ERROR: No valid API key found in .env file.")
    exit(1)

genai.configure(api_key=api_key)

print("\nListing ALL available models for this key:")
print("-" * 40)

try:
    models = genai.list_models()
    count = 0
    for m in models:
        # We only care about models that support content generation
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ {m.name}")
            count += 1
    
    if count == 0:
        print("⚠ No models found that support 'generateContent'.")
    else:
        print(f"\nFound {count} usable models.")

except Exception as e:
    print(f"❌ FAILED to list models: {str(e)}")
    print("\n💡 POSSIBLE CAUSES:")
    print("1. 'Generative Language API' is not enabled in Google Cloud Console.")
    print("2. The API key is restricted to specific APIs/Services.")
    print("3. Your region does not have access to these models.")

print("\n--- Diagnosis Finished ---")
