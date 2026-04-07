import requests
import xml.etree.ElementTree as ET
import time

BASE_URL = "http://127.0.0.1:5000"

def run_ivr_simulator():
    print("\n--- AgriSpark 2.0 IVR Voice Simulator (v2) ---")
    print("-" * 50)

    call_sid = "CA_simulated_call_123"
    from_no  = "+66812345678"
    current_url = "/ivr/welcome"
    params = {"CallSid": call_sid, "From": from_no}

    while current_url:
        try:
            response = requests.post(f"{BASE_URL}{current_url}", data=params)
            
            if response.status_code != 200:
                print(f"\n❌ Server Error ({response.status_code}): {response.text[:500]}")
                break
                
            try:
                root = ET.fromstring(response.text)
            except ET.ParseError:
                print(f"\n❌ XML Parsing Error. The server returned something that isn't TwiML.")
                print(f"--- START RESPONSE ---\n{response.text}\n--- END RESPONSE ---")
                break
            
            for element in root:
                if element.tag == "Say":
                    print(f"\n📢 AgriSpark Voice: \"{element.text}\"")
                    time.sleep(0.5)

                elif element.tag == "Gather":
                    for say in element.findall("Say"):
                        print(f"\n📢 AgriSpark Voice: \"{say.text}\"")
                    
                    if "speech" in element.get("input", "digits"):
                        user_input = input("\n🎤 [Microphone] Speak your answer: ").strip()
                        params["SpeechResult"] = user_input
                    else:
                        user_input = input("\n⌨️ [Keypad] Press digit(s): ").strip()
                        params["Digits"] = user_input
                    
                    current_url = element.get("action")
                    break

                elif element.tag == "Redirect":
                    current_url = element.text
                    print(f"\n(Redirecting to {current_url}...)")
                    break

                elif element.tag == "Hangup":
                    print("\n📵 [Call Ended by AgriSpark]")
                    current_url = None
                    break
            else:
                break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            break

if __name__ == "__main__":
    run_ivr_simulator()
