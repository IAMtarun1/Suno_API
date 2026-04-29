"""
Tests for the Ingestion Layer.

Owner: D (Dhir)
"""

import pytest
from unittest.mock import MagicMock
from contracts.interfaces import JobStatus
from modules.ingestion import handle_webhook


class MockRequest:
    """Mock Flask request object for testing."""

    def __init__(self, body="", sender="whatsapp:+1234567890", sid="test_sid"):
        self.form = {
            "Body": body,
            "From": sender,
            "MessageSid": sid,
        }


class TestHandleWebhook:

    def test_normal_message(self):
        req = MockRequest(body="a happy song about summer")
        result = handle_webhook(req)

        assert result.raw_prompt == "a happy song about summer"
        assert result.sender == "whatsapp:+1234567890"
        assert result.status == JobStatus.RECEIVED

    def test_empty_message(self):
        req = MockRequest(body="")
        result = handle_webhook(req)

        assert result.raw_prompt == ""
        assert result.status == JobStatus.RECEIVED  # Validation happens in logic layer

    def test_whitespace_message(self):
        req = MockRequest(body="   hello world   ")
        result = handle_webhook(req)

        assert result.raw_prompt == "hello world"  # Should be stripped

    def test_missing_fields(self):
        req = MockRequest(body="", sender="", sid="")
        result = handle_webhook(req)
        assert result.sender == ""
        assert result.raw_prompt == ""

    def test_long_message(self):
        long_msg = "a" * 500
        req = MockRequest(body=long_msg)
        result = handle_webhook(req)

        assert len(result.raw_prompt) == 500  # No truncation at ingestion level
