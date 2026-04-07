import sys
import os
from ai import gemini
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

def test_local_image(image_path):
    print(f"🔬 VISION TEST: Testing local file: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ ERROR: File not found at {image_path}")
        return

    try:
        # We read the file locally instead of downloading from Twilio
        with open(image_path, "rb") as f:
            img_data = f.read()
        
        print(f"✅ Loaded {len(img_data)} bytes. Sending to AgriSpark Brain...")
        
        # MOCKING the analyze_image logic for local testing
        # We'll use a direct call to the core AI logic in gemini.py (we need to expose it or reuse the logic)
        # For now, let's just use the analyze_image function by passing it a file:// URL if it supports it, 
        # or better, just call the Gemini logic directly in this script for a true isolation test.
        
        # Since analyze_image is currently hardcoded for Twilio HTTP requests, 
        # let's write a quick one-off for this CLI.
        
        from utils import prompts
        from ai.gemini import groq_client, _get_working_model
        import base64
        import time
        
        prompt_text = prompts.image_prompt("EN")
        ai_start = time.time()
        
        # 🧪 HYBRID VISION Logic (Gemini First for Stability)
        try:
            print("🤖 Testing with Gemini 1.5 Flash (Stable Vision)...")
            from PIL import Image
            from io import BytesIO
            image = Image.open(BytesIO(img_data))
            model = _get_working_model()
            resp = model.generate_content([prompt_text, image])
            ai_reply = resp.text.strip()
            
            # 🧩 STRATEGIC SEGMENTATION (What the farmer sees on WhatsApp)
            print(f"✅ SUCCESS (Gemini): Processed in {time.time() - ai_start:.2f}s")
            print("📦 DELIVERY SIMULATION (What arrives on WhatsApp):")
            chunks = gemini.split_message(ai_reply)
            for i, chunk in enumerate(chunks):
                print(f"\n--- MESSAGE PART {i+1} ({len(chunk)} chars) ---")
                print(chunk)
            print("\n" + "=" * 50)
            return
        except Exception as g_err:
            print(f"⚠️ Gemini Vision skipped/failed: {g_err}. Trying Groq...")

        if groq_client:
            print("🤖 Attempting Groq Vision fallback...")
            base64_image = base64.b64encode(img_data).decode('utf-8')
            # Trying the most likely new production IDs
            models_to_try = ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]
            for model_id in models_to_try:
                try:
                    completion = groq_client.chat.completions.create(
                        model=model_id,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }],
                        max_tokens=1024
                    )
                    print(f"✅ SUCCESS (Groq {model_id}): Processed in {time.time() - ai_start:.2f}s")
                    print("-" * 30)
                    print(completion.choices[0].message.content)
                    print("-" * 30)
                    return
                except Exception as v_err:
                    print(f"⚠️ Groq {model_id} failed: {v_err}")
            
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_vision.py path/to/image.jpg")
    else:
        test_local_image(sys.argv[1])
