"""
Delivery Layer — Send WhatsApp messages through Twilio.

Responsibilities:
- Send generated song audio
- Send progress updates
- Send clear user-facing error messages
- Keep Twilio failures from crashing the main pipeline
"""

import logging
from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from contracts.interfaces import SongResult
from config.settings import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_NUMBER,
)

logger = logging.getLogger(__name__)


ERROR_MESSAGES = {
    "invalid_prompt": (
        "❌ Your prompt is too short or empty.\n\n"
        "Send a clear song idea with at least a few words.\n\n"
        "Example:\n"
        "🎵 a happy pop song about summer"
    ),
    "blocked_content": (
        "🚫 I can’t process that prompt.\n\n"
        "Please try again with a safe and appropriate song idea."
    ),
    "generation_failed": (
        "⚠️ Something went wrong while generating your song.\n\n"
        "Please try again with a simpler prompt."
    ),
    "timeout": (
        "⏳ Song generation is taking longer than expected.\n\n"
        "Please try again in a few minutes."
    ),
    "delivery_failed": (
        "📛 Your song was generated, but I couldn’t send the audio file.\n\n"
        "Please try again."
    ),
    "rate_limit": (
        "⏳ Please wait a little before sending another song request.\n\n"
        "The bot can process one song at a time."
    ),
    "help": (
        "🎵 *Suno WhatsApp Song Bot* 🎵\n\n"
        "Send me a song idea and I’ll create an AI-generated song.\n\n"
        "*Examples:*\n"
        "• a Haryanvi song about cricket\n"
        "• a sad jazz song about finals week\n"
        "• a Punjabi pop song about friendship\n"
        "• an energetic rap about student life\n\n"
        "⏳ Real generation may take 1–3 minutes."
    ),
}


def _get_client() -> Optional[Client]:
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.error("Twilio credentials are missing. Check .env.")
        return None

    if not TWILIO_WHATSAPP_NUMBER:
        logger.error("TWILIO_WHATSAPP_NUMBER is missing. Check .env.")
        return None

    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def _send_text(to_number: str, body: str) -> bool:
    client = _get_client()

    if not client:
        return False

    try:
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number,
            body=body,
        )

        logger.info(f"WhatsApp text sent | SID: {message.sid} | To: {to_number}")
        return True

    except TwilioRestException as e:
        logger.error(
            f"Twilio text send failed | To: {to_number} | "
            f"Code: {e.code} | Msg: {e.msg}"
        )
        return False

    except Exception as e:
        logger.exception(f"Unexpected text delivery failure | To: {to_number}: {e}")
        return False


def _send_media(to_number: str, body: str, media_url: str) -> bool:
    client = _get_client()

    if not client:
        return False

    try:
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number,
            body=body,
            media_url=[media_url],
        )

        logger.info(
            f"WhatsApp media sent | SID: {message.sid} | "
            f"To: {to_number} | Media: {media_url}"
        )
        return True

    except TwilioRestException as e:
        logger.error(
            f"Twilio media send failed | To: {to_number} | "
            f"Code: {e.code} | Msg: {e.msg} | Media: {media_url}"
        )
        return False

    except Exception as e:
        logger.exception(f"Unexpected media delivery failure | To: {to_number}: {e}")
        return False


def resolve_error_message(error_type_or_message: str) -> str:
    """
    Accepts either:
    - a known error key like 'timeout'
    - a full custom message like '⚠️ Suno is out of credits...'
    """

    if not error_type_or_message:
        return ERROR_MESSAGES["generation_failed"]

    text = str(error_type_or_message).strip()

    if text in ERROR_MESSAGES:
        return ERROR_MESSAGES[text]

    # Treat already-human messages as final text.
    if text.startswith(("⚠️", "❌", "🚫", "⏳", "📛", "🎵", "📊", "✅")):
        return text

    # Fallback for unknown technical strings.
    return (
        "⚠️ Something went wrong while generating your song.\n\n"
        f"Reason: {text}"
    )


def send_processing_message(to_number: str, job_id: str = None) -> bool:
    job_line = f"\n🆔 Job ID: {job_id}" if job_id else ""

    body = (
        "🎵 Great prompt! Your song is being created.\n\n"
        "⏳ This can take 1–3 minutes because the bot is generating and downloading "
        "a real Suno track."
        f"{job_line}"
    )

    return _send_text(to_number, body)


def send_status_message(to_number: str) -> bool:
    body = (
        "📊 *Bot Status*\n\n"
        "✅ WhatsApp connected\n"
        "✅ Flask server running\n"
        "✅ Suno automation enabled\n\n"
        "Send a prompt like:\n"
        "🎵 a Hindi song about cricket"
    )

    return _send_text(to_number, body)


def send_examples_message(to_number: str) -> bool:
    body = (
        "🎶 *Example Prompts*\n\n"
        "• a Haryanvi song about cricket\n"
        "• a sad jazz song about finals week\n"
        "• a Punjabi pop song about friendship\n"
        "• an energetic rap about student life\n"
        "• a romantic Bollywood song about missing home"
    )

    return _send_text(to_number, body)


def send_error(to_number: str, error_type_or_message: str) -> bool:
    body = resolve_error_message(error_type_or_message)
    success = _send_text(to_number, body)

    if success:
        logger.info(f"User-facing error sent | To: {to_number} | Body: {body}")

    return success


def send_song(result: SongResult) -> bool:
    prompt = getattr(result.request, "raw_prompt", "your prompt")
    generation_time = getattr(result, "generation_time_sec", 0)

    body = (
        "✅ Your AI-generated song is ready!\n\n"
        f"🎧 Prompt: \"{prompt}\"\n"
        f"⏱️ Generated in {generation_time:.0f}s"
    )

    sent = _send_media(
        to_number=result.request.sender,
        body=body,
        media_url=result.media_url,
    )

    if sent:
        return True

    # Fallback: send the link as text if Twilio rejects media URL.
    fallback_body = (
        "✅ Your song was generated, but WhatsApp could not attach the audio file.\n\n"
        f"Open it here:\n{result.media_url}"
    )

    logger.warning(
        f"Media delivery failed. Sending fallback link instead: {result.media_url}"
    )

    return _send_text(result.request.sender, fallback_body)