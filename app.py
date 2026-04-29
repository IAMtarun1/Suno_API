"""
Suno WhatsApp Song Bot — Main Flask Application.

Owner: T (Tarun)

This is the orchestration layer that wires all modules together:
    1. Ingestion (D) → receives WhatsApp messages
    2. Logic (T) → validates and formats prompts
    3. Suno Bot (V) → generates songs via Selenium
    4. Delivery (D) → sends audio back via Twilio

Run: python app.py
"""

import os
import time
import logging
from flask import Flask, request, jsonify, send_from_directory

from contracts.interfaces import SongRequest, SongResult, JobStatus
from modules.ingestion import handle_webhook
from modules.logic import validate_and_format, get_help_message
from modules.delivery import send_song, send_error, send_processing_message
from modules.suno_bot import SunoBot
from config.settings import DOWNLOAD_DIR, NGROK_URL, FLASK_PORT

# ─── Flask App Setup ───────────────────────────────────────────────
app = Flask(__name__)
logger = logging.getLogger(__name__)

# ─── Suno Bot (initialized once, reused across requests) ──────────
# Set to None initially — initialized on first request or startup
suno_bot = None


def get_bot() -> SunoBot:
    """Get or initialize the SunoBot singleton."""
    global suno_bot
    if suno_bot is None:
        logger.info("Initializing SunoBot...")
        suno_bot = SunoBot(headless=False)
        if not suno_bot.login():
            logger.warning("Auto-login failed — trying manual login")
            suno_bot.manual_login()
    return suno_bot


# ─── Routes ────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "ok",
        "bot_initialized": suno_bot is not None,
        "download_dir": os.path.abspath(DOWNLOAD_DIR),
    }), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Main Twilio webhook endpoint.

    Full pipeline:
        1. Parse incoming WhatsApp message
        2. Validate and format the prompt
        3. Generate song via Suno
        4. Send audio back to user
    """
    # ── Step 1: Ingest ──────────────────────────────────────────
    song_req = handle_webhook(request)
    logger.info(f"Pipeline started | From: {song_req.sender} | Prompt: '{song_req.raw_prompt}'")

    # ── Step 2: Validate ────────────────────────────────────────
    song_req = validate_and_format(song_req)

    if song_req.status == JobStatus.FAILED:
        send_error(song_req.sender, song_req.error_message)
        return "", 200

    # ── Step 3: Acknowledge ─────────────────────────────────────
    send_processing_message(song_req.sender)

    # ── Step 4: Generate Song ───────────────────────────────────
    try:
        song_req.status = JobStatus.GENERATING
        bot = get_bot()

        start_time = time.time()
        file_path = bot.generate_song(song_req.formatted_prompt)
        gen_time = time.time() - start_time

        # Build public URL for Twilio to fetch the audio
        filename = os.path.basename(file_path)
        media_url = f"{NGROK_URL}/audio/{filename}"

        result = SongResult(
            request=song_req,
            file_path=file_path,
            media_url=media_url,
            generation_time_sec=gen_time,
            success=True
        )
        result.request.status = JobStatus.READY

        logger.info(f"Song generated in {gen_time:.1f}s | File: {filename}")

    except TimeoutError:
        logger.error("Song generation timed out")
        send_error(song_req.sender, "timeout")
        return "", 200

    except Exception as e:
        logger.error(f"Song generation failed: {e}")
        send_error(song_req.sender, "generation_failed")
        return "", 200

    # ── Step 5: Deliver ─────────────────────────────────────────
    if send_song(result):
        result.request.status = JobStatus.DELIVERED
        logger.info(f"✅ Pipeline complete | To: {song_req.sender}")
    else:
        send_error(song_req.sender, "delivery_failed")
        logger.error(f"❌ Delivery failed | To: {song_req.sender}")

    return "", 200


@app.route("/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    """
    Serve generated MP3 files publicly.

    Twilio needs a publicly accessible URL to fetch audio files.
    ngrok exposes this route, so the media_url becomes:
        {NGROK_URL}/audio/{filename}
    """
    return send_from_directory(
        os.path.abspath(DOWNLOAD_DIR),
        filename,
        mimetype="audio/mpeg"
    )


@app.route("/status", methods=["GET"])
def status():
    """Debug endpoint — shows current bot and system state."""
    import glob
    mp3_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp3"))

    return jsonify({
        "bot_initialized": suno_bot is not None,
        "ngrok_url": NGROK_URL,
        "download_dir": os.path.abspath(DOWNLOAD_DIR),
        "mp3_count": len(mp3_files),
        "mp3_files": [os.path.basename(f) for f in mp3_files],
    }), 200


# ─── Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(f"Starting Suno WhatsApp Bot on port {FLASK_PORT}")
    logger.info(f"Webhook URL: {NGROK_URL}/webhook")
    logger.info(f"Health check: http://localhost:{FLASK_PORT}/health")
    app.run(port=FLASK_PORT, debug=True, use_reloader=False)
