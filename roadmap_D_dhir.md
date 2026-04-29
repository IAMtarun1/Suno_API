# 🟦 DHIR's Complete Roadmap — Ingestion + Delivery + Testing + Documentation

> **Role:** WhatsApp I/O Engineer
> **Owns:** `modules/ingestion.py`, `modules/delivery.py`, Twilio setup, Testing framework, Documentation
> **Dependencies:** Only `contracts/interfaces.py` (already done)
> **Can start:** Immediately

---

## 📋 Your Files

| File | Purpose | Status |
|------|---------|--------|
| [ingestion.py](file:///Users/tarunthakur/Desktop/Suno%20API/modules/ingestion.py) | Parse Twilio webhook → SongRequest | ✅ Scaffolded |
| [delivery.py](file:///Users/tarunthakur/Desktop/Suno%20API/modules/delivery.py) | Send audio/errors back via Twilio | ✅ Scaffolded |
| [test_ingestion.py](file:///Users/tarunthakur/Desktop/Suno%20API/tests/test_ingestion.py) | Ingestion unit tests | ✅ 5 tests passing |
| [test_delivery.py](file:///Users/tarunthakur/Desktop/Suno%20API/tests/test_delivery.py) | Delivery unit tests | ✅ 4 tests passing |
| [test_integration.py](file:///Users/tarunthakur/Desktop/Suno%20API/tests/test_integration.py) | End-to-end tests | ✅ 6 tests passing |
| [test_results.md](file:///Users/tarunthakur/Desktop/Suno%20API/docs/test_results.md) | KPI tracking table | ✅ Template ready |

---

## 🗓️ DAY 1 — Twilio Sandbox + ngrok Setup

### Step 1.1: Create Twilio Account (30 min)

1. Go to [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up with email → verify phone number
3. From the Twilio Console dashboard, copy:
   - **Account SID** (starts with `AC...`)
   - **Auth Token** (click "Show" to reveal)
4. Open `/Users/tarunthakur/Desktop/Suno API/.env` and fill in:
   ```env
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   ```

### Step 1.2: Activate WhatsApp Sandbox (15 min)

1. In Twilio Console → **Messaging** → **Try it out** → **Send a WhatsApp message**
2. You'll see a sandbox number like `+14155238886`
3. It will show a join code like: **"join example-word"**
4. On your phone, open WhatsApp → send that join message to the sandbox number
5. You should get a confirmation reply: "You're connected!"
6. Update `.env`:
   ```env
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   ```

> [!IMPORTANT]
> **Every team member who wants to test must send the join message from their phone.** The sandbox only talks to registered numbers.

### Step 1.3: Install ngrok (15 min)

1. Go to [https://ngrok.com/download](https://ngrok.com/download) → Download for macOS
2. Or install via brew:
   ```bash
   brew install ngrok
   ```
3. Sign up at ngrok.com → copy your auth token
4. Configure:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```
5. Start ngrok (in a **separate terminal**, keep it running):
   ```bash
   ngrok http 5000
   ```
6. Copy the `https://xxxx-xx-xx.ngrok-free.app` URL
7. Update `.env`:
   ```env
   NGROK_URL=https://xxxx-xx-xx.ngrok-free.app
   ```

> [!WARNING]
> **ngrok URL changes every time you restart it** (unless you have a paid plan). Always update `.env` after restarting ngrok.

### Step 1.4: Connect Twilio to ngrok (10 min)

1. In Twilio Console → **Messaging** → **Settings** → **WhatsApp Sandbox Settings**
2. In **"When a message comes in"** field, paste:
   ```
   https://xxxx-xx-xx.ngrok-free.app/webhook
   ```
   (Use your actual ngrok URL)
3. Method: **POST**
4. Click **Save**

### Step 1.5: First Live Test (10 min)

1. Make sure the Flask server is running (T should have this going, or run it yourself):
   ```bash
   cd "/Users/tarunthakur/Desktop/Suno API"
   source venv/bin/activate
   python app.py
   ```
2. Send a WhatsApp message to the Twilio sandbox number from your phone
3. Check the Flask terminal — you should see:
   ```
   Webhook received | SID: SMxxxx | From: whatsapp:+1... | Message: 'your message'
   ```
4. 🎉 **If you see this, ingestion is working!**

**Troubleshooting:**
- If nothing happens → check ngrok terminal for incoming requests
- If ngrok shows 502 → Flask isn't running on port 5000
- If ngrok shows 404 → webhook URL is wrong (must end in `/webhook`)

---

## 🗓️ DAY 2 — Delivery Module Deep Implementation

### Step 2.1: Test Delivery with Real Audio (45 min)

The delivery module is already scaffolded. Now test it with a real audio file.

1. Create a quick test script:
   ```python
   # test_real_delivery.py (run manually, not with pytest)
   import os
   import sys
   sys.path.insert(0, os.path.dirname(__file__))
   
   from dotenv import load_dotenv
   load_dotenv()
   
   from modules.delivery import send_song, send_error, send_processing_message
   from contracts.interfaces import SongRequest, SongResult
   
   # Test 1: Send a text-only error message
   print("Test 1: Sending error message...")
   result = send_error("whatsapp:+1YOURNUMBER", "help")
   print(f"  Result: {result}")
   
   # Test 2: Send processing acknowledgment
   print("Test 2: Sending processing message...")
   result = send_processing_message("whatsapp:+1YOURNUMBER")
   print(f"  Result: {result}")
   
   # Test 3: Send a sample audio (use a public MP3 URL)
   print("Test 3: Sending sample audio...")
   req = SongRequest(sender="whatsapp:+1YOURNUMBER", raw_prompt="test song")
   song_result = SongResult(
       request=req,
       media_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
       generation_time_sec=42.0,
       success=True,
   )
   result = send_song(song_result)
   print(f"  Result: {result}")
   ```

2. Replace `+1YOURNUMBER` with your actual WhatsApp number
3. Run it:
   ```bash
   cd "/Users/tarunthakur/Desktop/Suno API"
   source venv/bin/activate
   python test_real_delivery.py
   ```
4. Check your WhatsApp — you should receive all 3 messages!

> [!TIP]
> If audio delivery fails but text works, the issue is likely the `media_url`. Twilio needs to be able to fetch the URL publicly. Test with the SoundHelix URL first to confirm Twilio works, then switch to the ngrok `/audio/` route.

### Step 2.2: Test the ngrok Audio Serving Route (30 min)

This is **critical** — when V's Suno bot downloads an MP3, we need Twilio to fetch it via ngrok.

1. Put any `.mp3` file in the `downloads/` folder:
   ```bash
   # Download a sample MP3 for testing
   curl -o "/Users/tarunthakur/Desktop/Suno API/downloads/test_song.mp3" \
     "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
   ```

2. With Flask + ngrok running, test the audio route in your browser:
   ```
   https://your-ngrok-url.ngrok-free.app/audio/test_song.mp3
   ```
   It should download/play the MP3.

3. Now test sending THIS URL via Twilio:
   ```python
   # Update the media_url in your test script:
   media_url = "https://your-ngrok-url.ngrok-free.app/audio/test_song.mp3"
   ```

4. If the audio arrives on WhatsApp → **the entire delivery pipeline is proven!** 🎉

### Step 2.3: Enhance Error Messages (30 min)

Open [delivery.py](file:///Users/tarunthakur/Desktop/Suno%20API/modules/delivery.py) and customize the error messages. Consider adding:

```python
# Add to ERROR_MESSAGES dict:
"rate_limit": (
    "🐌 Too many requests! Please wait a minute before trying again."
),
"server_error": (
    "🔧 Something went wrong on our end. We're looking into it.\n"
    "Please try again in a few minutes."
),
```

### Step 2.4: Add Delivery Tests for Edge Cases (30 min)

Open [test_delivery.py](file:///Users/tarunthakur/Desktop/Suno%20API/tests/test_delivery.py) and add:

```python
class TestSendProcessingMessage:

    @patch("modules.delivery.TWILIO_ACCOUNT_SID", "test_sid")
    @patch("modules.delivery.TWILIO_AUTH_TOKEN", "test_token")
    @patch("modules.delivery.Client")
    def test_send_processing_success(self, MockClient):
        from modules.delivery import send_processing_message
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = MagicMock(sid="SM999")
        assert send_processing_message("whatsapp:+1234567890") is True

    @patch("modules.delivery.TWILIO_ACCOUNT_SID", "")
    def test_send_processing_no_credentials(self):
        from modules.delivery import send_processing_message
        assert send_processing_message("whatsapp:+1234567890") is False
```

Run tests to verify: `python -m pytest tests/test_delivery.py -v`

---

## 🗓️ DAY 3–5 — Testing Infrastructure + Documentation

### Step 3.1: Build the Manual Test Harness (Day 3)

Create a script that simulates the full pipeline without needing a real phone:

```python
# tools/simulate_webhook.py
"""
Simulates a Twilio webhook POST to your Flask server.
Use this to test without needing a real WhatsApp message.

Usage: python tools/simulate_webhook.py "a happy song about coding"
"""
import requests
import sys

FLASK_URL = "http://localhost:5000/webhook"

def simulate(prompt: str):
    print(f"Simulating webhook with prompt: '{prompt}'")
    
    data = {
        "Body": prompt,
        "From": "whatsapp:+15551234567",
        "To": "whatsapp:+14155238886",
        "MessageSid": f"SM_TEST_{hash(prompt) % 10000:04d}",
    }
    
    response = requests.post(FLASK_URL, data=data)
    print(f"Response: {response.status_code} - {response.text}")

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a happy pop song about summer"
    simulate(prompt)
```

Test it:
```bash
mkdir -p tools
python tools/simulate_webhook.py "rock anthem about coding"
python tools/simulate_webhook.py ""          # Should get error
python tools/simulate_webhook.py "hi"        # Should get help
python tools/simulate_webhook.py "violence"  # Should get blocked
```

### Step 3.2: Document Setup Instructions (Day 4)

Create `docs/SETUP.md` with step-by-step setup instructions that any team member (or professor) can follow:

```markdown
# Setup Guide

## Prerequisites
- Python 3.10+
- Google Chrome browser
- Twilio account (free trial)
- ngrok account (free)

## Installation
1. Clone the repository
2. Create virtual environment: `python3 -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in credentials

## Running
1. Start ngrok: `ngrok http 5000`
2. Update NGROK_URL in `.env`
3. Update Twilio webhook URL
4. Start Flask: `python app.py`

## Testing
- Unit tests: `python -m pytest tests/ -v`
- Simulate webhook: `python tools/simulate_webhook.py "your prompt"`
```

### Step 3.3: Run Full Test Suite & Log Results (Day 5)

Execute the 10-test plan from [test_results.md](file:///Users/tarunthakur/Desktop/Suno%20API/docs/test_results.md):

1. Run each test scenario manually via WhatsApp or the simulator
2. Fill in the table with actual results
3. Calculate KPI metrics
4. Screenshot every test result on WhatsApp for the final presentation

### Step 3.4: Capture Screenshots for Presentation (Day 5)

Take screenshots of:
- [ ] Twilio Console showing sandbox config
- [ ] ngrok terminal showing incoming requests
- [ ] Flask terminal showing webhook logs
- [ ] WhatsApp conversation with bot responses
- [ ] Test results table (filled in)
- [ ] pytest output (30/30 passing)

Save all screenshots to `docs/screenshots/`

---

## 🗓️ DAY 6 — Integration Support

### Your Role on Integration Day:

| Task | Time |
|------|------|
| Verify Twilio credentials are in `.env` | 5 min |
| Start ngrok + update webhook URL | 5 min |
| Test webhook → Flask connectivity | 10 min |
| Test delivery with real audio from V's Suno output | 30 min |
| Run full pipeline test: WhatsApp → Song → WhatsApp | 30 min |
| Fix any delivery issues | As needed |

### Integration Checklist:

```
□ ngrok running and URL updated in .env
□ Twilio webhook pointing to ngrok URL
□ Flask server running
□ Can receive WhatsApp message (check Flask logs)
□ Can send text reply back to WhatsApp
□ Can send audio file back to WhatsApp
□ Full pipeline works end-to-end
```

---

## 🗓️ DAY 7 — Testing & Demo

### Morning: Execute All 10 Test Cases

Run through every test case from the test plan. For each one:

1. Send the prompt via WhatsApp
2. Note: success/fail, time taken, any error
3. Screenshot the WhatsApp conversation
4. Fill in `docs/test_results.md`

### Afternoon: Help with Demo

- Record the WhatsApp conversation for the demo video
- Finalize screenshots for the presentation
- Write the "Testing & Results" section of the final report

---

## ⚠️ Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Twilio returns 401 | Account SID or Auth Token is wrong in `.env` |
| ngrok shows "tunnel not found" | Restart ngrok, get new URL, update `.env` + Twilio |
| Audio doesn't play on WhatsApp | Check that `media_url` is publicly accessible via ngrok |
| WhatsApp says "sandbox expired" | Re-send the join message from your phone |
| Twilio "From number not valid" | Make sure number format is `whatsapp:+14155238886` |
| "Message body or media required" | The `body` or `media_url` parameter is empty |

---

## 📊 Your Deliverables Checklist

```
□ Twilio Sandbox configured and working
□ ngrok tunnel set up and documented
□ Delivery module tested with real audio
□ Webhook simulator script created
□ SETUP.md documentation written
□ 10 test cases executed and logged
□ Screenshots captured for presentation
□ Testing & Results report section drafted
```
