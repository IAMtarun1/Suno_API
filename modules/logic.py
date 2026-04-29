"""
Logic Layer — Prompt Validation and Formatting.

Owner: T (Tarun)

Responsibility:
    - Validate user input (length, content, format)
    - Apply content filtering (blocked words)
    - Format the prompt for Suno consumption
    - Return a processed SongRequest or mark it as FAILED
"""

import re
import logging
from contracts.interfaces import SongRequest, JobStatus
from config.settings import MAX_PROMPT_LENGTH, MIN_PROMPT_LENGTH

logger = logging.getLogger(__name__)

# Content filter — expand as needed
BLOCKED_WORDS = [
    "violence", "violent", "hate", "explicit", "nsfw",
    "kill", "murder", "abuse", "racist", "terrorism"
]

# Help commands that should return usage info, not generate a song
HELP_COMMANDS = ["help", "hi", "hello", "start", "menu", "?", "info"]


def validate_and_format(req: SongRequest) -> SongRequest:
    """
    Validate and format the user's raw prompt into a Suno-ready prompt.

    Validation checks (in order):
        1. Help command detection → returns help status
        2. Empty / too short → FAILED
        3. Too long → truncated
        4. Blocked content → FAILED
        5. Special character sanitization
        6. Prompt formatting for Suno

    Args:
        req: SongRequest with raw_prompt populated

    Returns:
        SongRequest with formatted_prompt set (or status=FAILED)
    """
    text = req.raw_prompt.strip()

    # ── Check for help commands ─────────────────────────────────
    if text.lower() in HELP_COMMANDS:
        req.status = JobStatus.FAILED
        req.error_message = "help"
        logger.info(f"Help command detected: '{text}'")
        return req

    # ── Length validation ────────────────────────────────────────
    if not text or len(text) < MIN_PROMPT_LENGTH:
        req.status = JobStatus.FAILED
        req.error_message = "invalid_prompt"
        logger.warning(f"Prompt too short ({len(text)} chars): '{text}'")
        return req

    if len(text) > MAX_PROMPT_LENGTH:
        logger.info(f"Prompt truncated from {len(text)} to {MAX_PROMPT_LENGTH} chars")
        text = text[:MAX_PROMPT_LENGTH]

    # ── Content filter ───────────────────────────────────────────
    text_lower = text.lower()
    for word in BLOCKED_WORDS:
        if word in text_lower:
            req.status = JobStatus.FAILED
            req.error_message = "blocked_content"
            logger.warning(f"Blocked word '{word}' found in prompt")
            return req

    # ── Sanitize special characters ──────────────────────────────
    # Keep alphanumeric, spaces, commas, periods, hyphens, apostrophes
    text = re.sub(r"[^\w\s,.\'\-!?]", "", text)

    # ── Format prompt for Suno ───────────────────────────────────
    req.formatted_prompt = f"Create a song about: {text}"
    req.status = JobStatus.VALIDATING
    logger.info(f"Prompt validated and formatted: '{req.formatted_prompt[:80]}'")

    return req


def get_help_message() -> str:
    """Return a friendly help/usage message for WhatsApp users."""
    return (
        "🎵 *Suno WhatsApp Song Bot* 🎵\n\n"
        "Send me a text description and I'll create a song for you!\n\n"
        "*How to use:*\n"
        "Just type what kind of song you want. For example:\n"
        '• "a happy pop song about summer vacation"\n'
        '• "sad jazz music about rainy days"\n'
        '• "upbeat rock anthem about coding"\n\n'
        f"*Rules:*\n"
        f"• Minimum {MIN_PROMPT_LENGTH} characters\n"
        f"• Maximum {MAX_PROMPT_LENGTH} characters\n"
        "• No inappropriate content\n\n"
        "⏳ Song generation takes about 60-90 seconds."
    )
