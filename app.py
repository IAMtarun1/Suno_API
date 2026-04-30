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
from modules.delivery import (
    send_processing_message,
    send_song,
    send_error,
    send_status_message,
    send_examples_message,
)

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
    FALLBACK_TO_MOCK_ON_FAILURE,
)

from contracts.interfaces import SongResult, JobStatus
from modules.ingestion import handle_webhook
from modules.logic import validate_and_format
from modules.suno_playwright import create_song_from_prompt, SunoCreditsError


app = Flask(__name__)
logger = logging.getLogger(__name__)

jobs = {}
last_request_time = defaultdict(lambda: datetime.min)
generation_lock = threading.Lock()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "app": "Suno WhatsApp Song Bot",
        "status": "running",
        "routes": [
            "/health",
            "/status",
            "/webhook",
            "/jobs",
            "/dashboard",
            "/audio/<filename>"
        ]
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "download_dir": DOWNLOAD_DIR,
        "mock_suno": MOCK_SUNO,
        "ngrok_url": NGROK_URL
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
        "mock_suno": MOCK_SUNO,
        "jobs_count": len(jobs)
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


@app.route("/dashboard", methods=["GET"])
def dashboard():
    mp3_files = [
        f for f in os.listdir(DOWNLOAD_DIR)
        if f.lower().endswith(".mp3")
    ] if os.path.exists(DOWNLOAD_DIR) else []

    job_rows = ""

    for job_id, job in jobs.items():
        status_value = job.get("status", "unknown")
        media_url = job.get("media_url", "")
        created_at = job.get("created_at", "")
        completed_at = job.get("completed_at", "")
        failed_at = job.get("failed_at", "")
        error = job.get("error", "")
        message = job.get("message", "")

        media_link = (
            f'<a href="{media_url}" target="_blank">Open Audio</a>'
            if media_url else "-"
        )

        job_rows += f"""
        <tr>
            <td>{job_id}</td>
            <td>{status_value}</td>
            <td>{media_link}</td>
            <td>{created_at}</td>
            <td>{completed_at or failed_at}</td>
            <td>{error}</td>
            <td>{message}</td>
        </tr>
        """

    audio_list = "".join([
        f'<li><a href="/audio/{quote(f)}" target="_blank">{f}</a></li>'
        for f in mp3_files
    ])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Suno WhatsApp Bot Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background: #f6f7fb;
                color: #222;
            }}
            .card {{
                background: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }}
            .badge {{
                display: inline-block;
                padding: 6px 10px;
                border-radius: 999px;
                background: #e8eefc;
                margin-right: 8px;
                margin-bottom: 8px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            th, td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
                text-align: left;
                font-size: 14px;
            }}
            th {{
                background: #f0f2f5;
            }}
            a {{
                color: #2563eb;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <h1>🎵 Suno WhatsApp Bot Dashboard</h1>
        <p>Live prototype monitoring page</p>

        <div class="card">
            <h2>System Status</h2>
            <span class="badge">Mock Suno: {MOCK_SUNO}</span>
            <span class="badge">Ngrok: {NGROK_URL}</span>
            <span class="badge">MP3 Files: {len(mp3_files)}</span>
            <span class="badge">Jobs: {len(jobs)}</span>
        </div>

        <div class="card">
            <h2>Downloaded Songs</h2>
            <ul>{audio_list}</ul>
        </div>

        <div class="card">
            <h2>Job History</h2>
            <table>
                <tr>
                    <th>Job ID</th>
                    <th>Status</th>
                    <th>Audio</th>
                    <th>Created</th>
                    <th>Finished</th>
                    <th>Error</th>
                    <th>Message</th>
                </tr>
                {job_rows}
            </table>
        </div>
    </body>
    </html>
    """

    return html, 200


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
    logger.info("WEBHOOK HIT")

    if not validate_twilio_signature():
        logger.error("Webhook rejected: Twilio signature validation failed")
        return "Forbidden", 403

    song_req = handle_webhook(request)
    logger.info(f"Pipeline started | From: {song_req.sender}")

    incoming_text = request.form.get("Body", "").strip().lower()

    if incoming_text == "status":
        send_status_message(song_req.sender)
        return "", 200

    if incoming_text == "examples":
        send_examples_message(song_req.sender)
        return "", 200

    if incoming_text.startswith("job "):
        requested_job_id = incoming_text.replace("job ", "").strip()

        job = jobs.get(requested_job_id)

        if not job:
            send_error(
                song_req.sender,
                f"❌ I couldn’t find job ID: {requested_job_id}"
            )
            return "", 200

        status = job.get("status", "unknown")
        media_url = job.get("media_url", "")
        message = job.get("message", "")

        reply = f"📊 Job {requested_job_id}\nStatus: {status}"

        if media_url:
            reply += f"\nAudio: {media_url}"

        if message:
            reply += f"\nMessage: {message}"

        send_error(song_req.sender, reply)
        return "", 200

    if is_rate_limited(song_req.sender):
        logger.warning(f"Rate limited sender: {song_req.sender}")
        send_error(
            song_req.sender,
            "⏳ Please wait a little before sending another song request."
        )
        return "", 200

    song_req = validate_and_format(song_req)

    if song_req.status == JobStatus.FAILED:
        send_error(song_req.sender, song_req.error_message)
        return "", 200

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "queued",
        "sender": song_req.sender,
        "created_at": datetime.now().isoformat()
    }

    send_processing_message(song_req.sender, job_id=job_id)

    thread = threading.Thread(
        target=_generate_and_deliver,
        args=(job_id, song_req),
        daemon=True
    )
    thread.start()

    return "", 200


def _generate_and_deliver(job_id, song_req):
    start_time = time.time()

    if not generation_lock.acquire(blocking=False):
        jobs[job_id] = {
            "status": "failed",
            "error": "bot_busy",
            "message": "Another song is currently being generated.",
            "failed_at": datetime.now().isoformat()
        }

        send_error(
            song_req.sender,
            "⏳ The bot is already generating another song. Please try again in a few minutes."
        )
        return

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
        reason = str(e)

        jobs[job_id] = {
            "status": "failed",
            "error": "out_of_credits",
            "message": reason,
            "failed_at": datetime.now().isoformat()
        }

        logger.error(f"Job {job_id} failed: {reason}")

        send_error(
            song_req.sender,
            f"⚠️ {reason}\n\nPlease try again after credits refresh."
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

        if FALLBACK_TO_MOCK_ON_FAILURE:
            try:
                logger.warning("Real Suno failed. Falling back to mock audio.")

                fallback_file = os.path.join(DOWNLOAD_DIR, "test_song.mp3")

                if os.path.exists(fallback_file):
                    filename = os.path.basename(fallback_file)
                    safe_filename = quote(filename)
                    media_url = f"{NGROK_URL}/audio/{safe_filename}"

                    result = SongResult(
                        request=song_req,
                        file_path=fallback_file,
                        media_url=media_url,
                        generation_time_sec=time.time() - start_time,
                        success=True
                    )

                    send_song(result)

                    jobs[job_id] = {
                        "status": "delivered_with_fallback",
                        "media_url": media_url,
                        "file_path": fallback_file,
                        "original_error": str(e),
                        "completed_at": datetime.now().isoformat()
                    }

                    return

            except Exception as fallback_error:
                logger.error(f"Fallback delivery failed: {fallback_error}")

        send_error(
            song_req.sender,
            "⚠️ Sorry, something went wrong while generating your song. Please try again."
        )

    finally:
        generation_lock.release()


if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    logger.info(f"Starting Suno WhatsApp Bot on port {PORT}")
    logger.info(f"Webhook URL: {NGROK_URL}/webhook")
    logger.info(f"Health check: http://localhost:{PORT}/health")
    logger.info(f"Dashboard: http://localhost:{PORT}/dashboard")
    logger.info(f"VALIDATE_TWILIO_SIGNATURE={VALIDATE_TWILIO_SIGNATURE}")
    logger.info(f"ALLOW_LOCAL_CURL={ALLOW_LOCAL_CURL}")
    logger.info(f"MOCK_SUNO={MOCK_SUNO}")

    app.run(
        host="127.0.0.1",
        port=PORT,
        debug=True
    )