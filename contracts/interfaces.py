"""
Shared contracts and data structures for the Suno WhatsApp Bot.

This module defines the shared data classes and function signatures
that all team members agree on. This is the decoupling mechanism
that allows D, T, and V to work independently.

Team Contract:
    D implements: handle_webhook(), send_song(), send_error()
    T implements: validate_and_format(), orchestration in app.py
    V implements: SunoBot.generate_song(), SunoBot.login()
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class JobStatus(Enum):
    """Tracks the lifecycle of a song generation request."""
    RECEIVED = "received"
    VALIDATING = "validating"
    GENERATING = "generating"
    READY = "ready"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class SongRequest:
    """
    Represents an incoming song generation request from WhatsApp.

    Created by D's ingestion layer, processed by T's logic layer,
    consumed by V's Suno bot.
    """
    sender: str                         # WhatsApp number (e.g., "whatsapp:+1234567890")
    raw_prompt: str                     # Original user message
    formatted_prompt: str = ""          # After logic layer processing
    status: JobStatus = JobStatus.RECEIVED
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: str = ""


@dataclass
class SongResult:
    """
    Represents the outcome of a song generation attempt.

    Created by the orchestration layer after V's Suno bot completes
    (or fails), consumed by D's delivery layer.
    """
    request: SongRequest
    file_path: Optional[str] = None     # Local path to downloaded MP3
    media_url: Optional[str] = None     # Public URL for Twilio to fetch
    error: Optional[str] = None
    generation_time_sec: float = 0.0
    success: bool = False
