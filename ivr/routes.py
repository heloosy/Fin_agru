"""
AgriSpark 2.0 — IVR Routes
All Twilio Voice webhook endpoints.
"""

import config
import threading
from flask import Blueprint, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather

from utils import session
from ai import gemini
from utils.weather import get_weather_summary
from pdf.generator import generate_pdf, get_pdf_url
from utils.delivery import send_whatsapp_pdf, send_sms
from ai.gemini import generate_sms_summary

ivr_bp = Blueprint("ivr", __name__, url_prefix="/ivr")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _say(resp: VoiceResponse, text: str, lang: str) -> None:
    """Add a <Say> with the correct voice for the language."""
    if lang == "EN":
        resp.say(text, voice="Polly.Joanna", language="en-US")
    else:
        # Using 'alice' for maximum compatibility as per user feedback
        resp.say(text, voice="alice", language="th-TH")


def _twiml(resp: VoiceResponse) -> Response:
    return Response(str(resp), mimetype="application/xml")


def _speech_lang(lang: str) -> str:
    return "en-US" if lang == "EN" else "th-TH"


# ─── STEP 0: Language Gate ────────────────────────────────────────────────────

@ivr_bp.route("/welcome", methods=["POST"])
def welcome():
    call_sid = request.form.get("CallSid", "unknown")
    session.set(call_sid, {"lang": "EN", "step": 1})   # default

    resp    = VoiceResponse()
    gather  = Gather(num_digits=1, action="/ivr/set-language", method="POST",
                     timeout=10)
    gather.say(
        "Welcome to AgriSpark 2.0, your visionary farming partner. I am here to help you grow more and earn more. "
        "Press 1 for English. Press 2 for Thai.",
        voice="Polly.Joanna", language="en-US"
    )
    gather.say(
        "ยินดีต้อนรับสู่ AgriSpark 2.0 หุ้นส่วนต้นคิดเพื่อการเกษตรของคุณ กด 1 สำหรับภาษาอังกฤษ กด 2 สำหรับภาษาไทย",
        voice="alice", language="th-TH"
    )
    resp.append(gather)
    # Fallback if no input
    resp.redirect("/ivr/welcome")
    return _twiml(resp)


@ivr_bp.route("/set-language", methods=["POST"])
def set_language():
    call_sid = request.form.get("CallSid", "unknown")
    digit    = request.form.get("Digits", "1").strip()
    lang     = "TH" if digit == "2" else "EN"
    session.update(call_sid, lang=lang)

    resp   = VoiceResponse()
    gather = Gather(num_digits=1, action="/ivr/set-mode", method="POST", timeout=10)

    if lang == "EN":
        gather.say(
            "Excellent. I am ready to assist. Press 1 for a quick agricultural consultation. "
            "Press 2 to design a full, professional farm plan specifically for your land.",
            voice="Polly.Joanna", language="en-US"
        )
    else:
        gather.say(
            "ยอดเยี่ยมมาก ฉันพร้อมช่วยเหลือคุณแล้ว กด 1 สำหรับการปรึกษาด้านการเกษตรอย่างรวดเร็ว "
            "กด 2 เพื่อรับการออกแบบแผนการเกษตรแบบมืออาชีพสำหรับพื้นที่ของคุณโดยเฉพาะ",
            voice="alice", language="th-TH"
        )

    resp.append(gather)
    resp.redirect("/ivr/set-language")
    return _twiml(resp)


# ─── STEP 1: Mode Gate ────────────────────────────────────────────────────────

@ivr_bp.route("/set-mode", methods=["POST"])
def set_mode():
    call_sid = request.form.get("CallSid", "unknown")
    digit    = request.form.get("Digits", "1").strip()
    lang     = session.get_lang(call_sid)
    mode     = "detailed" if digit == "2" else "quick"
    session.update(call_sid, mode=mode)

    resp = VoiceResponse()
    if mode == "quick":
        resp.redirect("/ivr/quickchat")
    else:
        resp.redirect("/ivr/collect")
    return _twiml(resp)


# ─── QUICK QUERY MODE: Conversation Loop ─────────────────────────────────────

@ivr_bp.route("/quickchat", methods=["POST"])
def quickchat():
    call_sid = request.form.get("CallSid", "unknown")
    lang     = session.get_lang(call_sid)
    resp     = VoiceResponse()

    prompt_text = (
        "Please speak your question after the tone. I am listening."
        if lang == "EN"
        else "กรุณาพูดคำถามของคุณหลังจากเสียงสัญญาณ ฉันกำลังฟังอยู่"
    )

    gather = Gather(
        input="speech",
        language=_speech_lang(lang),
        action="/ivr/quickreply",
        method="POST",
        speech_timeout="auto",
        timeout=5,
    )
    _say_gather(gather, prompt_text, lang)
    resp.append(gather)

    # Fallback if nothing spoken
    if lang == "EN":
        resp.say("I didn't catch that. Let me try again.", voice="Polly.Joanna", language="en-US")
    else:
        resp.say("ฉันไม่ได้ยิน ลองอีกครั้ง", voice="alice", language="th-TH")
    resp.redirect("/ivr/quickchat")
    return _twiml(resp)


def _say_gather(gather, text: str, lang: str):
    if lang == "EN":
        gather.say(text, voice="Polly.Joanna", language="en-US")
    else:
        # Using 'alice' for maximum compatibility as per user feedback
        gather.say(text, voice="alice", language="th-TH")


@ivr_bp.route("/quickreply", methods=["POST"])
def quickreply():
    call_sid   = request.form.get("CallSid", "unknown")
    lang       = session.get_lang(call_sid)
    transcript = request.form.get("SpeechResult", "").strip()

    resp = VoiceResponse()

    if not transcript:
        resp.redirect("/ivr/quickchat")
        return _twiml(resp)

    # Store conversation for context
    history = session.get(call_sid).get("history", [])
    history.append({"role": "user", "text": transcript})

    try:
        ai_reply = gemini.quick_answer(lang, transcript)
    except Exception as e:
        ai_reply = ("Sorry, I had trouble with that. Please repeat your question."
                    if lang == "EN"
                    else "ขอโทษ มีปัญหา กรุณาถามอีกครั้ง")

    history.append({"role": "model", "text": ai_reply})
    session.update(call_sid, history=history[-20:])

    _say(resp, ai_reply, lang)

    # Ask if they have another question
    gather = Gather(
        num_digits=1,
        action="/ivr/quickchat-again",
        method="POST",
        timeout=8,
    )
    follow_up = (
        "Press 1 to ask another question, or press 2 to end the call."
        if lang == "EN"
        else "กด 1 เพื่อถามคำถามอื่น หรือกด 2 เพื่อวางสาย"
    )
    _say_gather(gather, follow_up, lang)
    resp.append(gather)
    resp.redirect("/ivr/goodbye")
    return _twiml(resp)


@ivr_bp.route("/quickchat-again", methods=["POST"])
def quickchat_again():
    call_sid = request.form.get("CallSid", "unknown")
    digit    = request.form.get("Digits", "2").strip()
    resp     = VoiceResponse()
    if digit == "1":
        resp.redirect("/ivr/quickchat")
    else:
        resp.redirect("/ivr/goodbye")
    return _twiml(resp)


# ─── DETAILED PLAN MODE: 6-Step Wizard ───────────────────────────────────────

STEPS_EN = [
    ("name",         "What is your name?"),
    ("location",     "What is the location or province of your farm field?"),
    ("past_crop",    "What crop did you grow last season?"),
    ("current_crop", "What crop are you planning to grow this season?"),
    ("soil_type",    "What is your soil type? Say sandy, clay, loam, or unknown."),
    ("terrain",      "Describe your terrain. Say flat, hilly, sloped, or near water."),
]

STEPS_TH = [
    ("name",         "ชื่อของคุณคืออะไร?"),
    ("location",     "ฟาร์มของคุณอยู่ที่ไหน หรือจังหวัดอะไร?"),
    ("past_crop",    "ฤดูที่ผ่านมาคุณปลูกพืชอะไร?"),
    ("current_crop", "ฤดูนี้คุณวางแผนจะปลูกพืชอะไร?"),
    ("soil_type",    "ประเภทดินของคุณคือ ดินทราย ดินเหนียว ดินร่วน หรือไม่ทราบ?"),
    ("terrain",      "สภาพพื้นที่ของคุณเป็นอย่างไร ราบเรียบ ลูกคลื่น ลาดเอียง หรือใกล้น้ำ?"),
]


@ivr_bp.route("/collect", methods=["POST"])
def collect():
    call_sid = request.form.get("CallSid", "unknown")
    lang     = session.get_lang(call_sid)
    step     = session.get_step(call_sid)   # 1–6
    steps    = STEPS_TH if lang == "TH" else STEPS_EN

    if step > len(steps):
        return _twiml(VoiceResponse())  # safety

    _, question = steps[step - 1]

    resp = VoiceResponse()

    # Intro message on step 1
    if step == 1:
        intro = (
            "Great! I will ask you 6 quick questions to build your personalised farm plan. "
            if lang == "EN"
            else "ดีมาก! ฉันจะถามคุณ 6 คำถามสั้นๆ เพื่อสร้างแผนการเกษตรส่วนตัวของคุณ "
        )
        _say(resp, intro, lang)

    gather = Gather(
        input="speech",
        language=_speech_lang(lang),
        action="/ivr/collect-answer",
        method="POST",
        speech_timeout="auto",
        timeout=8,
    )
    _say_gather(gather, question, lang)
    resp.append(gather)

    # Fallback
    no_answer = ("I didn't hear you. Please try again." if lang == "EN"
                 else "ฉันไม่ได้ยิน กรุณาลองอีกครั้ง")
    _say(resp, no_answer, lang)
    resp.redirect("/ivr/collect")
    return _twiml(resp)


@ivr_bp.route("/collect-answer", methods=["POST"])
def collect_answer():
    call_sid   = request.form.get("CallSid", "unknown")
    lang       = session.get_lang(call_sid)
    transcript = request.form.get("SpeechResult", "").strip()
    step       = session.get_step(call_sid)
    steps      = STEPS_TH if lang == "TH" else STEPS_EN

    if not transcript:
        # Re-ask the same question
        resp = VoiceResponse()
        resp.redirect("/ivr/collect")
        return _twiml(resp)

    field_key = steps[step - 1][0]
    
    # 🧠 LIGHTNING UPGRADE: Clean the messy speech transcript
    try:
        clean_text = gemini.clean_ivr_answer(lang, field_key, transcript)
        print(f"🎙️ VOICE CLARITY: Raw='{transcript}' -> Clean='{clean_text}'")
        session.update(call_sid, **{field_key: clean_text})
    except Exception:
        session.update(call_sid, **{field_key: transcript})

    resp = VoiceResponse()
    if step < len(steps):
        session.increment_step(call_sid)
        resp.redirect("/ivr/collect")
    else:
        # All 6 steps done
        done_msg = (
            "Thank you! I have everything I need. Generating your personalised farm plan now. "
            "This will take just a moment."
            if lang == "EN"
            else "ขอบคุณ! ฉันมีข้อมูลครบแล้ว กำลังสร้างแผนการเกษตรส่วนตัวของคุณ โปรดรอสักครู่"
        )
        _say(resp, done_msg, lang)
        resp.redirect("/ivr/complete")
    return _twiml(resp)


# ─── COMPLETION: Generate Plan + Send Deliveries ──────────────────────────────

@ivr_bp.route("/complete", methods=["POST"])
def complete():
    call_sid = request.form.get("CallSid", "unknown")
    lang     = session.get_lang(call_sid)
    
    from_no  = request.form.get("From", "")
    to_no    = request.form.get("To", "")
    
    # 🧠 ASYNC POWER-UP: Launch heavy processing in a background thread ⚡
    # This prevents Twilio's "Application Error" (Timeout) while AI & PDF generate.
    thread = threading.Thread(
        target=_process_complete,
        args=(call_sid, lang, from_no, to_no)
    )
    thread.daemon = True
    thread.start()

    resp = VoiceResponse()
    msg = (
        "Thank you! I am generating your personalised farm plan now. "
        "It will be sent to your WhatsApp in just a moment. Goodbye!"
        if lang == "EN"
        else "ขอบคุณ! ฉันกำลังสร้างแผนการเกษตรส่วนตัวของคุณ "
             "และจะส่งให้คุณทาง WhatsApp ในอีกครู่เดียวเท่านั้น ลาก่อน!"
    )
    _say(resp, msg, lang)
    resp.hangup()
    
    # Note: Session is deleted inside the background thread once done.
    return _twiml(resp)


def _process_complete(call_sid, lang, from_no, to_no):
    """Heavy-lifting executed in background to satisfy Twilio timeouts."""
    try:
        system_nos = [config.TWILIO_PHONE.strip(), config.TWILIO_WHATSAPP.replace("whatsapp:", "").strip()]
        farmer_no  = from_no
        if from_no.strip() in system_nos:
            farmer_no = to_no

        sess = session.get(call_sid)
        profile = {
            "name":         sess.get("name",         "Farmer"),
            "location":     sess.get("location",      "Unknown"),
            "past_crop":    sess.get("past_crop",     "Unknown"),
            "current_crop": sess.get("current_crop",  "Unknown"),
            "soil_type":    sess.get("soil_type",     "Unknown"),
            "terrain":      sess.get("terrain",       "Unknown"),
        }

        # 🏛️ Save to persistent archive
        if farmer_no:
            session.save_farmer_profile(farmer_no, profile)
            print(f"📡 AGENTIC SYNC: Linked IVR data for {farmer_no}")

        # 1. Weather
        weather = get_weather_summary(profile["location"])

        # 2. AI Plan
        plan_text = gemini.generate_farm_plan(lang, profile, weather)

        # 3. PDF
        pdf_path = generate_pdf(profile, plan_text, lang)
        pdf_url  = get_pdf_url(pdf_path)

        # 4. SMS Summary
        sms_text = generate_sms_summary(lang, profile, plan_text[:500])

        # 5. Deliveries
        if farmer_no:
            print(f"📡 AGENTIC DELIVERY: Processing WhatsApp for {farmer_no}")
            
            try:
                wa_body = gemini.generate_wa_summary(lang, plan_text)
                send_whatsapp_pdf(farmer_no, wa_body, pdf_url)
                print("✅ WhatsApp Sent!")
            except Exception as e:
                print(f"❌ WhatsApp Error: {e}")

            try:
                send_sms(farmer_no, sms_text)
                print("✅ SMS Sent!")
            except Exception as e:
                print(f"❌ SMS Error: {e}")

    except Exception as e:
        print(f"❌ Background Processing Error: {e}")
    finally:
        session.delete(call_sid)


# ─── Goodbye ─────────────────────────────────────────────────────────────────

@ivr_bp.route("/goodbye", methods=["POST"])
def goodbye():
    call_sid = request.form.get("CallSid", "unknown")
    lang     = session.get_lang(call_sid)
    resp     = VoiceResponse()
    msg = (
        "Thank you for calling AgriSpark. Wishing you a great harvest. Goodbye!"
        if lang == "EN"
        else "ขอบคุณที่โทรหา AgriSpark ขอให้คุณประสบความสำเร็จในการเก็บเกี่ยว ลาก่อน!"
    )
    _say(resp, msg, lang)
    resp.hangup()
    return _twiml(resp)
