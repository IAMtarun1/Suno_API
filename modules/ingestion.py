"""
Ingestion Layer — Twilio WhatsApp Webhook Handler.

Owner: D (Dhir)

Responsibility:
    - Receive incoming WhatsApp messages from Twilio webhook
    - Parse sender info and message body
    - Create a SongRequest object for downstream processing
"""

import logging
from contracts.interfaces import SongRequest, JobStatus

logger = logging.getLogger(__name__)


def handle_webhook(request) -> SongRequest:
    """
    Parse an incoming Twilio webhook request into a SongRequest.

    Twilio sends POST data with these relevant fields:
        - Body: The text message content
        - From: Sender's WhatsApp number (e.g., "whatsapp:+1234567890")
        - To: Your Twilio WhatsApp number
        - MessageSid: Unique message identifier

    Args:
        request: Flask request object from the webhook POST

    Returns:
        SongRequest with sender and raw_prompt populated
    """
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")
    message_sid = request.form.get("MessageSid", "unknown")

    logger.info(
        f"Webhook received | SID: {message_sid} | From: {sender} | "
        f"Message: '{incoming_msg[:50]}{'...' if len(incoming_msg) > 50 else ''}'"
    )

    song_request = SongRequest(
        sender=sender,
        raw_prompt=incoming_msg,
        formatted_prompt="",
        status=JobStatus.RECEIVED
    )

    return song_request
