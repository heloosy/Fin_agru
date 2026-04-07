"""
AgriSpark 2.0 — Flask Application Entry Point
"""

import os
from flask import Flask, send_from_directory

import config

def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY

    # Ensure PDF output directory exists
    os.makedirs(config.PDF_DIR, exist_ok=True)

    # ── Register Blueprints ────────────────────────────────────────────────
    from ivr.routes      import ivr_bp
    from whatsapp.routes import wa_bp

    app.register_blueprint(ivr_bp)
    app.register_blueprint(wa_bp)

    # ── Serve PDFs statically ──────────────────────────────────────────────
    @app.route("/static/pdf/<filename>")
    def serve_pdf(filename):
        return send_from_directory(config.PDF_DIR, filename)

    # ── Health check ───────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        return {"status": "ok", "service": "AgriSpark 2.0"}, 200

    # ── Render Frontend ──────────────────────────────────────────────────
    from flask import render_template, jsonify, request
    from twilio.rest import Client

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/trigger-call", methods=["POST"])
    def trigger_call():
        data = request.json
        phone_number = data.get("phone")

        if not phone_number:
            return jsonify({"success": False, "error": "Phone number is required"}), 400

        if not config.TWILIO_PHONE:
            return jsonify({"success": False, "error": "System Error: TWILIO_PHONE_NUMBER is not configured in environment variables."}), 500

        try:
            client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
            call = client.calls.create(
                to=phone_number,
                from_=config.TWILIO_PHONE,
                url=f"{config.BASE_URL}/ivr/welcome"
            )
            return jsonify({"success": True, "call_sid": call.sid})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/web-chat", methods=["POST"])
    def web_chat():
        from ai import gemini
        data = request.json
        message = data.get("message")
        history = data.get("history", [])
        lang = data.get("lang", "EN")

        if not message:
            return jsonify({"error": "No message provided"}), 400

        try:
            reply = gemini.chat_reply(lang, message, history)
            return jsonify({"reply": reply})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

# Create the application object for production servers (like Gunicorn/Railway)
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
