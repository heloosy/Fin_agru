"""
AgriSpark 2.0 — Session & State Manager
Handles ephemeral IVR sessions and persistent farmer profiles.
"""

import os
import json
import time

# --- Configuration ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

PROFILES_FILE = os.path.join(DATA_DIR, "profiles.json")
HISTORY_FILE  = os.path.join(DATA_DIR, "wa_history.json")

# Ephemeral in-memory store for active calls/sessions
_SESSIONS = {}

# --- Persistent Loading/Saving ---

def _load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving session data to {path}: {e}")

# --- Core Session API (Ephemeral) ---

def get(session_id):
    """Retrieve session data by ID (CallSid or Phone). Returns dict."""
    return _SESSIONS.get(session_id, {})

def set(session_id, data):
    """Set the entire session data for an ID."""
    _SESSIONS[session_id] = data

def update(session_id, **kwargs):
    """Update specific fields in a session."""
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {}
    _SESSIONS[session_id].update(kwargs)

def delete(session_id):
    """Remove a session from memory."""
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]

def get_lang(session_id):
    return _SESSIONS.get(session_id, {}).get("lang", "EN")

def get_step(session_id):
    return _SESSIONS.get(session_id, {}).get("step", 1)

def increment_step(session_id):
    curr = get_step(session_id)
    update(session_id, step=curr + 1)

# --- Farmer Profiles (Persistent) ---

def save_farmer_profile(phone, profile_data):
    """Save/update a farmer's profile linked to their phone number."""
    profiles = _load_json(PROFILES_FILE)
    profiles[phone] = profile_data
    _save_json(PROFILES_FILE, profiles)

def load_farmer_profile(phone):
    """Load a farmer's profile. Returns dict with defaults if not found."""
    profiles = _load_json(PROFILES_FILE)
    return profiles.get(phone, {
        "name": "Farmer",
        "location": "Unknown",
        "past_crop": "Unknown",
        "current_crop": "Unknown",
        "soil_type": "Unknown",
        "terrain": "Unknown",
        "detail_mode": "medium"  # brief, medium, deep
    })

def update_detail_mode(phone, mode):
    """Safely update a farmer's preferred detail mode."""
    profiles = _load_json(PROFILES_FILE)
    if phone in profiles:
        profiles[phone]["detail_mode"] = mode
    else:
        # Create fresh profile with just the mode
        profiles[phone] = load_farmer_profile(phone)
        profiles[phone]["detail_mode"] = mode
    _save_json(PROFILES_FILE, profiles)

# --- WhatsApp History (Persistent) ---

def get_wa_history(phone):
    """Retrieve chat history for a WhatsApp user."""
    histories = _load_json(HISTORY_FILE)
    return histories.get(phone, [])

def append_wa_history(phone, role, text):
    """Add a new message to the chat history and persist it."""
    histories = _load_json(HISTORY_FILE)
    if phone not in histories:
        histories[phone] = []
    
    histories[phone].append({
        "role": role,
        "text": text,
        "timestamp": time.time()
    })
    
    # Keep only last 20 messages for Gemini context efficiency
    histories[phone] = histories[phone][-20:]
    _save_json(HISTORY_FILE, histories)
