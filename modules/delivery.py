"""
Delivery Layer — Send Audio Back via Twilio WhatsApp.

Owner: D (Dhir)

Responsibility:
    - Send generated song audio back to the user via Twilio
    - Send error messages for various failure modes
    - Send help/usage messages
"""

import logging
from twilio.rest import Client
from contracts.interfaces import SongResult
from config.settings import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_NUMBER
)

logger = logging.getLogger(__name__)

# ─── Error Messages Catalog ────────────────────────────────────────
ERROR_MESSAGES = {
    "invalid_prompt": (
        "❌ Your prompt is too short or empty.\n"
        "Please send a descriptive text (at least 3 characters).\n\n"
        'Example: "a happy pop song about summer"'
    ),
    "blocked_content": (
        "🚫 Your prompt contains content that we can't process.\n"
        "Please try again with appropriate content."
    ),
    "generation_failed": (
        "⚠️ Song generation failed. Please try again in a moment."
    ),
    "timeout": (
        "⏳ Song generation is taking too long.\n"
        "Please try a simpler or shorter prompt."
    ),
    "delivery_failed": (
        "📛 We generated your song but couldn't send it.\n"
        "Please try again."
    ),
    "help": (
        "🎵 *Suno WhatsApp Song Bot* 🎵\n\n"
        "Send me a text description and I'll create a song!\n\n"
        "*Examples:*\n"
        '• "a happy pop song about summer"\n'
        '• "sad jazz about rainy days"\n\n'
        "⏳ Takes about 60-90 seconds."
    ),
}


def _get_client():
    """Get a Twilio client, or None if credentials are missing."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.error("Twilio credentials not configured in .env")
        return None
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_song(result: SongResult) -> bool:
    """
    Send the generated song audio back to the user via WhatsApp.

    Args:
        result: SongResult with media_url populated

    Returns:
        True if the message was sent successfully
    """
    client = _get_client()
    if not client:
        return False

    try:
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=(
                "🎵 Here's your AI-generated song!\n\n"
                f"Prompt: \"{result.request.raw_prompt}\"\n"
                f"⏱️ Generated in {result.generation_time_sec:.0f}s"
            ),
            media_url=[result.media_url],
            to=result.request.sender
        )
        logger.info(f"Song delivered | SID: {message.sid} | To: {result.request.sender}")
        return True
    except Exception as e:
        logger.error(f"Delivery failed to {result.request.sender}: {e}")
        return False


def send_error(to_number: str, error_type: str) -> bool:
    """
    Send an error message to the user via WhatsApp.

    Args:
        to_number: Recipient's WhatsApp number
        error_type: Key from ERROR_MESSAGES dict

    Returns:
        True if the message was sent successfully
    """
    client = _get_client()
    if not client:
        return False

    body = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["generation_failed"])
    try:
        client.messages.create(from_=TWILIO_WHATSAPP_NUMBER, body=body, to=to_number)
        logger.info(f"Error message sent | Type: {error_type} | To: {to_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to send error to {to_number}: {e}")
        return False


def send_processing_message(to_number: str) -> bool:
    """
    Send a 'processing' acknowledgment so the user knows we're working.

    Args:
        to_number: Recipient's WhatsApp number

    Returns:
        True if sent successfully
    """
    client = _get_client()
    if not client:
        return False

    try:
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body="🎵 Great prompt! Your song is being created...\n⏳ Please wait ~60-90 seconds.",
            to=to_number
        )
        logger.info(f"Processing message sent to {to_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to send processing msg to {to_number}: {e}")
        return False
