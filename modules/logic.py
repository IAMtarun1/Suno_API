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
from config.settings import USE_AI_PROMPT_ENHANCER
from modules.prompt_ai import enhance_prompt_with_ai

logger = logging.getLogger(__name__)

# Content filter — expand as needed
BLOCKED_WORDS = [
    "violence", "violent", "hate", "explicit", "nsfw",
    "kill", "murder", "abuse", "racist", "terrorism"
]

# Help commands that should return usage info, not generate a song
HELP_COMMANDS = ["help", "hi", "hello", "start", "menu", "?", "info"]

GENRE_KEYWORDS = {
    "pop": "catchy pop",
    "jazz": "smooth jazz",
    "rock": "energetic rock",
    "rap": "rhythmic rap",
    "hip hop": "modern hip hop",
    "punjabi": "upbeat Punjabi",
    "haryanvi": "energetic Haryanvi folk-pop",
    "bollywood": "cinematic Bollywood",
    "sad": "emotional sad",
    "romantic": "romantic soft",
    "cricket": "energetic sports anthem",
}


def detect_style(text):
    text_lower = text.lower()

    styles = []

    for keyword, style in GENRE_KEYWORDS.items():
        if keyword in text_lower:
            styles.append(style)

    return ", ".join(styles)


def validate_and_format(req: SongRequest) -> SongRequest:
    """
    Validate the user's raw prompt and convert it into a Suno-ready prompt.

    Flow:
        1. Detect help commands
        2. Validate prompt length
        3. Block unsafe content
        4. Sanitize text
        5. Optionally enhance with AI
        6. Format final Suno prompt
    """
    text = req.raw_prompt.strip()

    # ── Help command detection ───────────────────────────────────
    if text.lower() in HELP_COMMANDS:
        req.status = JobStatus.FAILED
        req.error_message = "help"
        logger.info(f"Help command detected: '{text}'")
        return req

    # ── Basic validation ─────────────────────────────────────────
    if not text or len(text) < MIN_PROMPT_LENGTH:
        req.status = JobStatus.FAILED
        req.error_message = "invalid_prompt"
        logger.warning(f"Prompt too short ({len(text)} chars): '{text}'")
        return req

    if len(text) > MAX_PROMPT_LENGTH:
        logger.info(f"Prompt truncated from {len(text)} to {MAX_PROMPT_LENGTH} chars")
        text = text[:MAX_PROMPT_LENGTH]

    # ── Content filtering ────────────────────────────────────────
    text_lower = text.lower()

    for word in BLOCKED_WORDS:
        if word in text_lower:
            req.status = JobStatus.FAILED
            req.error_message = "blocked_content"
            logger.warning(f"Blocked word '{word}' found in prompt")
            return req

    # ── Sanitize text ────────────────────────────────────────────
    text = re.sub(r"[^\w\s,.\'\-!?]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # ── Optional AI prompt enhancement ───────────────────────────
    try:
        if USE_AI_PROMPT_ENHANCER:
            enhanced_text = enhance_prompt_with_ai(text)

            if enhanced_text:
                logger.info(f"AI-enhanced prompt: '{enhanced_text[:100]}'")
                text = enhanced_text

    except Exception as e:
        logger.warning(f"AI prompt enhancement failed, using original prompt: {e}")

    # ── Final Suno formatting ────────────────────────────────────
    style = detect_style(text)

    if style:
        req.formatted_prompt = (
            f"Create a short {style} song about: {text}. "
            f"Make it catchy, clear, and suitable for a 40-50 second prototype demo."
        )
    else:
        req.formatted_prompt = (
            f"Create a short catchy song about: {text}. "
            f"Make it clear, musical, and suitable for a 40-50 second prototype demo."
        )

    req.status = JobStatus.VALIDATING

    logger.info(f"Prompt validated and formatted: '{req.formatted_prompt[:100]}'")

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
