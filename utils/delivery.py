"""
AgriSpark 2.0 — Delivery Helpers
Send WhatsApp messages and SMS via Twilio.
"""

from twilio.rest import Client
import config


def _client() -> Client:
    return Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)


def send_whatsapp_text(to: str, body: str) -> str:
    """Send a WhatsApp text message. `to` should be E.164 number."""
    to_wa = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
    from_wa = config.TWILIO_WHATSAPP.strip()
    
    if to_wa == from_wa:
        print(f"⚠️ SELF-SEND DETECTED: Skipping WhatsApp message to {to_wa} (sender and receiver are identical).")
        return "self-send-skipped"

    msg = _client().messages.create(
        to=to_wa,
        from_=from_wa,
        body=body,
    )
    return msg.sid


def send_whatsapp_pdf(to: str, body: str, pdf_url: str) -> str:
    """Send a WhatsApp message with a PDF attachment."""
    to_wa = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
    from_wa = config.TWILIO_WHATSAPP.strip()

    if to_wa == from_wa:
        print(f"⚠️ SELF-SEND DETECTED: Skipping WhatsApp media to {to_wa}.")
        return "self-send-skipped"

    msg = _client().messages.create(
        to=to_wa,
        from_=from_wa,
        body=body,
        media_url=[pdf_url],
    )
    return msg.sid


def send_sms(to: str, body: str) -> str:
    """Send a plain SMS."""
    # Strip whatsapp: prefix if present
    to_num = to.replace("whatsapp:", "").strip()
    from_num = config.TWILIO_PHONE.strip()

    if to_num == from_num:
        print(f"⚠️ SELF-SEND DETECTED: Skipping SMS to {to_num}.")
        return "self-send-skipped"

    msg = _client().messages.create(
        to=to_num,
        from_=from_num,
        body=body,
    )
    return msg.sid
