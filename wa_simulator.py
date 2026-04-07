import os
import sys
from dotenv import load_dotenv

# Ensure local paths are found
sys.path.append(os.path.dirname(__file__))

from ai import gemini
from utils import session

# Load keys
load_dotenv()

MENU_EN = """🌾 *AgriSpark 2.0* — Your AI Farming Advisor

Commands:
• *plan* — Get a personalised farm plan (PDF)
• *weather* — 7-day weather for your location
• *price* — Crop market price guidance
• *help* — Show this menu

Or just ask me anything about farming! Send a photo of your crop for instant diagnosis. 🌿"""

MENU_TH = """🌾 *AgriSpark 2.0* — ที่ปรึกษาการเกษตร AI ของคุณ

คำสั่ง:
• *plan* — รับแผนการเกษตรส่วนตัว (PDF)
• *weather* — พยากรณ์อากาศ 7 วัน
• *price* — ข้อมูลราคาพืชผล
• *help* — แสดงเมนูนี้

หรือถามฉันเรื่องการเกษตรได้เลย! ส่งรูปพืชของคุณเพื่อการวินิจฉัยทันที 🌿"""

def run_simulator():
    phone = "whatsapp:+123456789"
    print("\n--- AgriSpark 2.0 Terminal Simulator ---")
    print("Type 'exit' to quit. Test commands: 'plan', 'stop', 'weather'.")
    print("-" * 40)

    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit' or user_input.lower() == 'quit':
            break

        # Check for commands first (simulating the logic in routes.py)
        body_lower = user_input.lower().strip()
        sess = session.get(phone)
        lang = sess.get("lang", "EN")

        if body_lower in ("help", "menu", "start", "ช่วย", "เมนู"):
            print(f"\nAgriSpark:\n{MENU_TH if lang == 'TH' else MENU_EN}")
            continue
        
        if body_lower in ("stop", "cancel", "exit"):
            session.update(phone, plan_step=0, awaiting=None)
            print("\nAgriSpark: ✅ Stopped. You are back in general chat.")
            continue

        if body_lower == "plan":
            session.update(phone, plan_step=1, plan_data={})
            print("\nAgriSpark: 🌾 Let's build your plan! 1️⃣ What is your name?")
            continue

        # If in plan mode
        plan_step = sess.get("plan_step", 0)
        if plan_step > 0:
            # Simple simulation of step increment
            session.update(phone, plan_step=plan_step + 1)
            print(f"\nAgriSpark: [Saved answer]. Next question step {plan_step + 1}...")
            continue

        # General Chat
        print("\nAgriSpark (Thinking...):")
        try:
            history = session.get_wa_history(phone)
            reply = gemini.chat_reply("EN", user_input, history)
            session.append_wa_history(phone, "model", reply)
            print(f"{reply}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    run_simulator()
