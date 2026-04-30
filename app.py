import os
import time
import uuid
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import quote

from flask import Flask, request, jsonify, send_from_directory
from twilio.request_validator import RequestValidator
from modules.suno_playwright import create_song_from_prompt, SunoCreditsError

from config.settings import (
    PORT,
    NGROK_URL,
    DOWNLOAD_DIR,
    MOCK_SUNO,
    SUNO_HEADLESS,
    TWILIO_AUTH_TOKEN,
    VALIDATE_TWILIO_SIGNATURE,
    ALLOW_LOCAL_CURL,
    RATE_LIMIT_SEC,
)

from contracts.interfaces import SongResult, JobStatus
from modules.ingestion import handle_webhook
from modules.logic import validate_and_format
from modules.delivery import send_processing_message, send_song, send_error
from modules.suno_playwright import create_song_from_prompt


app = Flask(__name__)
logger = logging.getLogger(__name__)

jobs = {}
last_request_time = defaultdict(lambda: datetime.min)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "app": "Suno WhatsApp Song Bot",
        "status": "running",
        "routes": ["/health", "/status", "/webhook", "/jobs", "/audio/<filename>"]
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "download_dir": DOWNLOAD_DIR,
        "mock_suno": MOCK_SUNO
    }), 200


@app.route("/status", methods=["GET"])
def status():
    mp3_files = [
        f for f in os.listdir(DOWNLOAD_DIR)
        if f.lower().endswith(".mp3")
    ] if os.path.exists(DOWNLOAD_DIR) else []

    return jsonify({
        "ngrok_url": NGROK_URL,
        "download_dir": DOWNLOAD_DIR,
        "mp3_count": len(mp3_files),
        "mp3_files": mp3_files,
        "mock_suno": MOCK_SUNO
    }), 200


@app.route("/jobs", methods=["GET"])
def list_jobs():
    return jsonify(jobs), 200


@app.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    job = jobs.get(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job), 200


@app.route("/audio/<path:filename>", methods=["GET"])
def serve_audio(filename):
    return send_from_directory(
        DOWNLOAD_DIR,
        filename,
        mimetype="audio/mpeg",
        as_attachment=False
    )


def is_local_request():
    return request.remote_addr in ("127.0.0.1", "::1", "localhost")


def validate_twilio_signature():
    if not VALIDATE_TWILIO_SIGNATURE:
        return True

    if ALLOW_LOCAL_CURL and is_local_request():
        logger.warning("Skipping Twilio signature validation for local curl request")
        return True

    signature = request.headers.get("X-Twilio-Signature", "")

    if not signature:
        logger.warning("Missing X-Twilio-Signature header")
        return False

    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    public_url = f"{NGROK_URL}{request.path}"

    is_valid = validator.validate(
        public_url,
        request.form,
        signature
    )

    if not is_valid:
        logger.warning(f"Invalid Twilio signature for URL: {public_url}")

    return is_valid


def is_rate_limited(sender):
    now = datetime.now()
    last_time = last_request_time[sender]

    if now - last_time < timedelta(seconds=RATE_LIMIT_SEC):
        return True

    last_request_time[sender] = now
    return False


@app.route("/webhook", methods=["POST"])
def webhook():
    logger.info("WEBHOOK HIT - BEFORE VALIDATION")
    # if not validate_twilio_signature():
    #     logger.error("REJECTING WEBHOOK WITH 403")
    #     return "Forbidden", 403

    song_req = handle_webhook(request)
    logger.info(f"Pipeline started | From: {song_req.sender}")

    if is_rate_limited(song_req.sender):
        logger.warning(f"Rate limited sender: {song_req.sender}")
        send_error(song_req.sender, "rate_limit")
        return "", 200

    song_req = validate_and_format(song_req)

    if song_req.status == JobStatus.FAILED:
        send_error(song_req.sender, song_req.error_message)
        return "", 200

    send_processing_message(song_req.sender)

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "generating",
        "sender": song_req.sender,
        "created_at": datetime.now().isoformat()
    }

    thread = threading.Thread(
        target=_generate_and_deliver,
        args=(job_id, song_req),
        daemon=True
    )
    thread.start()

    return "", 200


def _generate_and_deliver(job_id, song_req):
    start_time = time.time()

    try:
        jobs[job_id]["status"] = "generating"

        if MOCK_SUNO:
            logger.info("MOCK MODE: Simulating song generation")
            time.sleep(5)
            file_path = os.path.join(DOWNLOAD_DIR, "test_song.mp3")
        else:
            logger.info("REAL SUNO MODE: Generating song with Playwright")
            file_path = create_song_from_prompt(
                song_req.formatted_prompt,
                headless=SUNO_HEADLESS
            )

        gen_time = time.time() - start_time

        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Generated file not found: {file_path}")

        filename = os.path.basename(file_path)
        safe_filename = quote(filename)
        media_url = f"{NGROK_URL}/audio/{safe_filename}"

        result = SongResult(
            request=song_req,
            file_path=file_path,
            media_url=media_url,
            generation_time_sec=gen_time,
            success=True
        )

        send_song(result)

        jobs[job_id] = {
            "status": "delivered",
            "media_url": media_url,
            "file_path": file_path,
            "generation_time": round(gen_time, 2),
            "completed_at": datetime.now().isoformat()
        }

        logger.info(f"Job {job_id} completed successfully in {gen_time:.2f}s")

    except SunoCreditsError as e:
        jobs[job_id] = {
            "status": "failed",
            "error": "out_of_credits",
            "message": str(e),
            "failed_at": datetime.now().isoformat()
        }

        logger.error(f"Job {job_id} failed: Suno out of credits")

        send_error(
            song_req.sender,
            "⚠️ Suno account is out of credits. Please recharge or switch account."
        )

    except TimeoutError as e:
        jobs[job_id] = {
            "status": "failed",
            "error": "timeout",
            "message": str(e),
            "failed_at": datetime.now().isoformat()
        }

        logger.error(f"Job {job_id} timed out: {e}")

        send_error(
            song_req.sender,
            "⏳ Song generation took too long. Please try again later."
        )

    except Exception as e:
        jobs[job_id] = {
            "status": "failed",
            "error": "generation_failed",
            "message": str(e),
            "failed_at": datetime.now().isoformat()
        }

        logger.exception(f"Job {job_id} failed unexpectedly")

        send_error(
            song_req.sender,
            "⚠️ Sorry, something went wrong while generating your song. Please try again."
        )


if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    logger.info(f"Starting Suno WhatsApp Bot on port {PORT}")
    logger.info(f"Webhook URL: {NGROK_URL}/webhook")
    logger.info(f"Health check: http://localhost:{PORT}/health")

    logger.info(f"VALIDATE_TWILIO_SIGNATURE={VALIDATE_TWILIO_SIGNATURE}")
    logger.info(f"ALLOW_LOCAL_CURL={ALLOW_LOCAL_CURL}")

    app.run(
        host="127.0.0.1",
        port=PORT,
        debug=True
    )