"""
AgriSpark 2.0 — WhatsApp Bot Routes
Handles inbound WhatsApp messages: text and images with full agentic AI.
"""

from flask import Blueprint, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import traceback

from utils import session
from ai import gemini
from utils.weather import get_weather_summary
from pdf.generator import generate_pdf, get_pdf_url
from utils.delivery import send_whatsapp_pdf, send_sms
from ai.gemini import generate_sms_summary, generate_farm_plan, extract_profile_from_history
import config

wa_bp = Blueprint("whatsapp", __name__, url_prefix="")

# ─── Menu messages ────────────────────────────────────────────────────────────

MENU_EN = """🌾 *AgriSpark 2.0* — Your AI Farming Advisor

Commands:
• *plan* — Personalised farm plan (PDF)
• *weather* — 7-day weather forecast
• *price* — Market price guidance
• */brief*, */medium*, */deep* — Toggle message size

Or just ask me anything! Send a photo for instant diagnosis. 🌿"""

MENU_TH = """🌾 *AgriSpark 2.0* — ที่ปรึกษาการเกษตร AI ของคุณ

คำสั่ง:
• *plan* — รับแผนการเกษตรส่วนตัว (PDF)
• *weather* — พยากรณ์อากาศ 7 วัน
• *price* — ข้อมูลราคาพืชผล
• */brief*, */medium*, */deep* — ปรับระดับความละเอียดของคำตอบ

หรือถามฉันเรื่องการเกษตรได้เลย! ส่งรูปพืชของคุณเพื่อการวินิจฉัยทันที 🌿"""

# ─── Main WhatsApp webhook ────────────────────────────────────────────────────

@wa_bp.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    ai_reply = ""
    try:
        from_number  = request.form.get("From", "")
        body         = request.form.get("Body", "").strip()
        num_media    = int(request.form.get("NumMedia", 0))
        media_url    = request.form.get("MediaUrl0", "")
        media_type   = request.form.get("MediaContentType0", "")

        # Load / initialize session
        sess = session.get(from_number)
        lang = sess.get("lang", None)

        if lang is None:
            if body:
                lang = gemini.detect_language(body)
            else:
                lang = "EN"
            session.update(from_number, lang=lang)

        resp = MessagingResponse()
        # Removed pre-created msg = resp.message() to avoid empty first message

        # ─── Image received ───────────────────────────────────────────────────────
        if num_media > 0 and media_url and "image" in media_type:
            try:
                print(f"📸 WHATSAPP: Processing incoming image from {from_number}...")
                analysis = gemini.analyze_image(
                    lang, media_url,
                    config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN
                )
                session.append_wa_history(from_number, "user", "[Image sent]")
                session.append_wa_history(from_number, "model", analysis)
                
                # 🧩 Split and send chunks (Fix for Error 21617)
                for chunk in gemini.split_message(analysis):
                    resp.message(chunk)
                return Response(str(resp), mimetype="application/xml")
            except Exception as vision_e:
                print(f"❌ WHATSAPP VISION ERROR: {vision_e}")
                resp.message("⚠️ I saw your photo but had trouble analyzing it. Please try again or check my logs!" if lang == "EN" else "⚠️ ฉันเห็นภาพของคุณแล้ว แต่มีปัญหาในการวิเคราะห์ กรุณาลองใหม่อีกครั้ง")
                return Response(str(resp), mimetype="application/xml")

        # ─── Text commands ────────────────────────────────────────────────────────
        body_lower = body.lower().strip()

        # Commands
        if body_lower in ("help", "menu", "ช่วย", "เมนู", "start"):
            resp.message(MENU_TH if lang == "TH" else MENU_EN)
            return Response(str(resp), mimetype="application/xml")

        if body_lower in ("reset", "restart", "เริ่มใหม่"):
            session.delete(from_number)
            resp.message("✅ Reset. How can I help you today?" if lang == "EN" else "✅ รีเซ็ตแล้ว มีอะไรให้ฉันช่วยไหม?")
            return Response(str(resp), mimetype="application/xml")

        if body_lower in ("stop", "cancel", "exit", "หยุด", "ยกเลิก"):
            session.update(from_number, plan_step=0, awaiting=None)
            resp.message("✅ Stopped. Ask me anything!" if lang == "EN" else "✅ ยกเลิกแล้ว ถามฉันได้เลย!")
            return Response(str(resp), mimetype="application/xml")

        # ─── Detail Mode Toggles ──────────────────────────────────────
        if body_lower in ("/brief", "/short", "/สั้น"):
            session.update_detail_mode(from_number, "brief")
            msg.body("⚡ *MODE: BRIEF*\n\nI will now keep my answers quick and concise." if lang == "EN" else "⚡ *โหมด: กะทัดรัด*\n\nฉันจะตอบคำถามสั้นๆ ได้ใจความ")
            return Response(str(resp), mimetype="application/xml")
            
        if body_lower in ("/medium", "/standard", "/ปกติ"):
            session.update_detail_mode(from_number, "medium")
            msg.body("⚖️ *MODE: MEDIUM*\n\nI will now provide balanced, high-yield advice." if lang == "EN" else "⚖️ *โหมด: ปกติ*\n\nฉันจะให้คำแนะนำระดับพรีเมียมตามปกติ")
            return Response(str(resp), mimetype="application/xml")
            
        if body_lower in ("/deep", "/detail", "/detailed", "/ละเอียด"):
            session.update_detail_mode(from_number, "deep")
            msg.body("🧪 *MODE: DEEP ANALYSIS*\n\nI will now provide extreme technical depth for every answer." if lang == "EN" else "🧪 *โหมด: ละเอียดเชิงลึก*\n\nฉันจะให้คำแนะนำเชิงเทคนิคขั้นสูงในระดับลึกที่สุด")
            return Response(str(resp), mimetype="application/xml")

        if body_lower in ("weather", "อากาศ"):
            stored_loc = sess.get("location") or sess.get("plan_data", {}).get("location")
            if stored_loc:
                summary = get_weather_summary(stored_loc)
                header = f"*🌦 WEATHER: {stored_loc.upper()}*" if lang == "EN" else f"*🌦 พยากรณ์อากาศ: {stored_loc}*"
                resp.message(f"{header}\n\n\n{summary}")
            else:
                session.update(from_number, awaiting="weather_location")
                ask = "📊 *WEATHER DISCOVERY*\n\n\nWhich location do you want weather for?" if lang == "EN" else "📊 *ค้นหาพยากรณ์อากาศ*\n\n\nคุณต้องการพยากรณ์อากาศของที่ไหน?"
                resp.message(ask)
            return Response(str(resp), mimetype="application/xml")

        if body_lower in ("price", "ราคา"):
            resp.message(_market_price_info(lang))
            return Response(str(resp), mimetype="application/xml")

        # ─── Awaiting weather location ────────────────────────────────
        if sess.get("awaiting") == "weather_location":
            session.update(from_number, location=body, awaiting=None)
            summary = get_weather_summary(body)
            header = f"*🌦 WEATHER: {body.upper()}*" if lang == "EN" else f"*🌦 พยากรณ์อากาศ: {body}*"
            resp.message(f"{header}\n\n\n{summary}")
            return Response(str(resp), mimetype="application/xml")

        # ─── AGENTIC CHATBOT ──────────────────────────────────────────
        history = session.get_wa_history(from_number)
        profile = session.load_farmer_profile(from_number)
        
        try:
            # Get response
            ai_reply = gemini.chat_reply(lang, body, history, profile)
            
            # Save history
            session.append_wa_history(from_number, "user", body)
            session.append_wa_history(from_number, "model", ai_reply)

            # 🏛️ MASTER MEMORY RESTORE: Load data from phone-linked archive
            # Only trigger plan generation if the AI explicitly requests it
            if "[GENERATE_PLAN]" in ai_reply:
                master_profile = session.load_farmer_profile(from_number)
                
                # Extract any brand new info from current chat history
                extracted = extract_profile_from_history(history + [{"role": "user", "text": body}])
                
                # MERGE: Master Data + Extracted New Data
                profile = {**master_profile, **extracted}
                
                # Filter out "Unknown" if we have better data in either set
                for k in profile:
                    if str(profile[k]).lower() == "unknown":
                        profile[k] = master_profile.get(k, "Unknown")
                
                print(f"📡 AGENTIC RESTORE: Synced Master Archive for {from_number}")
                
                # SMART ADAPTATION: Use defaults if STILL missing
                if not profile.get("name") or profile.get("name").lower() == "unknown":
                    profile["name"] = "Farmer"
                
                loc = profile.get("location", "Unknown")
                weather_text = get_weather_summary(loc) if loc.lower() != "unknown" else "Weather details will be more accurate once you share your location!"
                
                # Build plan
                full_plan = generate_farm_plan(lang, profile, weather_text)
                
                try:
                    pdf_path = generate_pdf(profile, full_plan, lang)
                    pdf_url  = get_pdf_url(pdf_path)
                    send_whatsapp_pdf(from_number, f"📄 Plan for {profile.get('name', 'you')} is ready!", pdf_url)
                    
                    sms_short = generate_sms_summary(lang, profile, full_plan[:300])
                    send_sms(from_number, sms_short)
                    
                    ai_reply += "\n\n✅ DONE! I've sent your PDF plan to WhatsApp and SMS."
                    
                    # Gently nudge for more info if location was missing
                    if loc.lower() == "unknown":
                        ai_reply += "\n\n(Tip: Tell me your *Location* next time for a hyper-local weather forecast! 🌦️)"
                except Exception as pdf_err:
                    ai_reply += f"\n\n⚠️ (PDF Issue: {str(pdf_err)[:40]}...)"

        except Exception as e:
            print(f"Chat error: {traceback.format_exc()}")
            ai_reply = (f"I had a thinking hiccup. Please try again! ({str(e)[:40]})" 
                        if lang == "EN" else f"ขอโทษ มีปัญหาในการประมวลผล กรุณาลองอีกครั้ง ({str(e)[:40]})")

        if not str(ai_reply).strip():
            ai_reply = "I'm thinking... please ask that again!" if lang == "EN" else "กำลังประมวลผล... กรุณาลองใหม่อีกครั้ง"
            
        # 🧩 Split and send chunks (Fix for Error 21617)
        for chunk in gemini.split_message(ai_reply):
            resp.message(chunk)
            
        return Response(str(resp), mimetype="application/xml")
    
    except Exception as fatal_e:
        tb = traceback.format_exc()
        print(f"FATAL: {tb}")
        err_log = f"🆘 *AgriSpark Fatal Error:*\n{str(fatal_e)}\n\n*Traceback:*\n{tb[:400]}"
        resp = MessagingResponse()
        resp.message(err_log)
        return Response(str(resp), mimetype="application/xml")

# ─── Price Helper ─────────────────────────────────────────────────────────────

def _market_price_info(lang: str) -> str:
    if lang == "TH":
        return "💰 *ราคาพืชผลล่าสุด*\n\n🌾 ข้าว: 12,000 บาท/ตัน\n🌽 ข้าวโพด: 8,000 บาท/ตัน"
    return "💰 *Approximate Crop Prices*\n\n🌾 Rice: 12,000 THB/ton\n🌽 Corn: 8,000 THB/ton"
