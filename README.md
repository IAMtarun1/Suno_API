# 🎵 Suno WhatsApp Song Bot

A full-stack AI-powered WhatsApp bot that transforms text prompts into songs using **Twilio WhatsApp + Flask + Playwright + Suno**.

Users send a text prompt through WhatsApp (example: *“a Hindi song about cricket”*), and the bot automatically generates and delivers a downloadable AI-generated song.

---

# 🚀 Features

## Core Functionality
- WhatsApp message ingestion via Twilio Sandbox
- Flask backend webhook pipeline
- Prompt validation + enhancement
- Real Suno automation using Playwright
- Persistent Chrome profile login (avoids repeated OAuth)
- Auto-download generated MP3
- Audio delivery back to WhatsApp
- Job queue + dashboard monitoring

---

# 🛡️ Production-Oriented Features
- Rate limiting
- Bot busy lock (single generation queue)
- Twilio signature validation support
- Local dev bypass
- Out-of-credits detection
- Credit refresh timer extraction
- Timeout handling
- Delivery fallback if media fails
- Dashboard for monitoring jobs and downloads

---

# 🧠 Example User Flow

## User:
```txt
a Haryanvi song about cricket

Bot:
🎵 Great prompt! Your song is being created.
⏳ This can take 1–3 minutes...
Final:
✅ Your AI-generated song is ready!



🏗️ Architecture
WhatsApp User
     ↓
Twilio Sandbox Webhook
     ↓
Flask (/webhook)
     ↓
Prompt Validation + Formatting
     ↓
Playwright + Suno Automation
     ↓
Song Download (MP3)
     ↓
Twilio WhatsApp Delivery



📂 Project Structure
Suno API/
│
├── app.py                     # Main Flask server
├── config/
│   └── settings.py           # Environment config
│
├── modules/
│   ├── ingestion.py          # Twilio webhook parsing
│   ├── logic.py              # Prompt validation/formatting
│   ├── delivery.py           # WhatsApp messaging
│   └── suno_playwright.py    # Suno browser automation
│
├── contracts/
│   └── interfaces.py         # Shared request/result objects
│
├── downloads/                # Generated songs
├── chrome_profile/           # Persistent Suno login session
├── tests/                    # Testing files
│
├── .env
├── .env.example
└── README.md