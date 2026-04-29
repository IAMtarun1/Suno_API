"""
Integration Tests — End-to-End Pipeline.

Owner: ALL (Day 6-7)

These tests verify that all modules work together correctly.
Run these after merging all individual modules.
"""

import pytest
from unittest.mock import patch, MagicMock
from contracts.interfaces import SongRequest, SongResult, JobStatus
from modules.ingestion import handle_webhook
from modules.logic import validate_and_format


class MockFlaskRequest:
    """Mock Flask request for integration testing."""
    def __init__(self, body, sender="whatsapp:+1234567890"):
        self.form = {
            "Body": body,
            "From": sender,
            "MessageSid": "test_integration",
        }


class TestIngestionToLogicPipeline:
    """Test that ingestion output feeds correctly into logic layer."""

    def test_valid_prompt_flows_through(self):
        req = MockFlaskRequest("a rock song about mountains")
        song_req = handle_webhook(req)
        song_req = validate_and_format(song_req)

        assert song_req.status == JobStatus.VALIDATING
        assert "mountains" in song_req.formatted_prompt

    def test_empty_prompt_caught_by_logic(self):
        req = MockFlaskRequest("")
        song_req = handle_webhook(req)
        song_req = validate_and_format(song_req)

        assert song_req.status == JobStatus.FAILED

    def test_help_command_caught_by_logic(self):
        req = MockFlaskRequest("help")
        song_req = handle_webhook(req)
        song_req = validate_and_format(song_req)

        assert song_req.status == JobStatus.FAILED
        assert song_req.error_message == "help"

    def test_blocked_content_caught_by_logic(self):
        req = MockFlaskRequest("a song glorifying violence")
        song_req = handle_webhook(req)
        song_req = validate_and_format(song_req)

        assert song_req.status == JobStatus.FAILED
        assert song_req.error_message == "blocked_content"


class TestResultCreation:
    """Test that SongResult objects are correctly constructed."""

    def test_successful_result(self):
        req = SongRequest(
            sender="whatsapp:+1234567890",
            raw_prompt="summer vibes",
            formatted_prompt="Create a song about: summer vibes",
            status=JobStatus.GENERATING,
        )

        result = SongResult(
            request=req,
            file_path="/downloads/song.mp3",
            media_url="https://ngrok.io/audio/song.mp3",
            generation_time_sec=55.3,
            success=True,
        )

        assert result.success is True
        assert result.request.sender == "whatsapp:+1234567890"
        assert result.generation_time_sec < 60

    def test_failed_result(self):
        req = SongRequest(
            sender="whatsapp:+1234567890",
            raw_prompt="test",
            status=JobStatus.GENERATING,
        )

        result = SongResult(
            request=req,
            error="Timeout",
            success=False,
        )

        assert result.success is False
        assert result.file_path is None
