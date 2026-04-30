"""
Application-wide configuration and logging setup.

Owner: T (Tarun)
"""

import os
import logging
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# ─── Directory Paths ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
LOG_DIR = os.path.join(BASE_DIR, "logs")
COOKIE_FILE = os.path.join(BASE_DIR, "config", "suno_cookies.json")
MOCK_SUNO = os.getenv("MOCK_SUNO", "false").lower() == "true"
VALIDATE_TWILIO_SIGNATURE = os.getenv("VALIDATE_TWILIO_SIGNATURE", "true").lower() == "true"
ALLOW_LOCAL_CURL = os.getenv("ALLOW_LOCAL_CURL", "false").lower() == "true"
RATE_LIMIT_SEC = int(os.getenv("RATE_LIMIT_SEC", "60"))
SUNO_HEADLESS = os.getenv("SUNO_HEADLESS", "false").lower() == "true"
PORT = int(os.getenv("PORT", "5000"))

# Ensure required directories exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ─── Environment Variables ─────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

SUNO_EMAIL = os.getenv("SUNO_EMAIL", "")
SUNO_PASSWORD = os.getenv("SUNO_PASSWORD", "")

NGROK_URL = os.getenv("NGROK_URL", "http://localhost:5000")

# ─── App Constants ──────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_PROMPT_LENGTH = 200
MIN_PROMPT_LENGTH = 3
GENERATION_TIMEOUT_SEC = 120
POLL_INTERVAL_SEC = 5
FLASK_PORT = 5000

# ─── Logging Setup ─────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(module)-15s | %(message)s"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # Also print to console
    ]
)

# Suppress noisy third-party loggers
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger with the app's configuration."""
    return logging.getLogger(name)
