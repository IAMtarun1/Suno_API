"""
Tests for the Logic Layer.

Owner: T (Tarun)
"""

import pytest
from contracts.interfaces import SongRequest, JobStatus
from modules.logic import validate_and_format, get_help_message


def make_request(prompt: str) -> SongRequest:
    """Helper to create a SongRequest for testing."""
    return SongRequest(
        sender="whatsapp:+1234567890",
        raw_prompt=prompt,
    )


class TestValidateAndFormat:

    def test_valid_prompt(self):
        req = make_request("a happy song about summer")
        result = validate_and_format(req)

        assert result.status == JobStatus.VALIDATING
        assert "Create a song about:" in result.formatted_prompt
        assert "summer" in result.formatted_prompt

    def test_empty_prompt(self):
        req = make_request("")
        result = validate_and_format(req)

        assert result.status == JobStatus.FAILED
        assert result.error_message == "invalid_prompt"

    def test_too_short(self):
        req = make_request("ab")
        result = validate_and_format(req)

        assert result.status == JobStatus.FAILED
        assert result.error_message == "invalid_prompt"

    def test_exactly_min_length(self):
        req = make_request("abc")
        result = validate_and_format(req)

        assert result.status == JobStatus.VALIDATING

    def test_long_prompt_truncated(self):
        long_prompt = "a" * 300
        req = make_request(long_prompt)
        result = validate_and_format(req)

        assert result.status == JobStatus.VALIDATING
        # Formatted prompt = "Create a song about: " + truncated text
        assert len(result.formatted_prompt) < 300

    def test_blocked_word(self):
        req = make_request("a song about violence and destruction")
        result = validate_and_format(req)

        assert result.status == JobStatus.FAILED
        assert result.error_message == "blocked_content"

    def test_blocked_word_case_insensitive(self):
        req = make_request("a song about VIOLENCE")
        result = validate_and_format(req)

        assert result.status == JobStatus.FAILED

    def test_help_command(self):
        for cmd in ["help", "hi", "hello", "start", "menu", "?"]:
            req = make_request(cmd)
            result = validate_and_format(req)

            assert result.status == JobStatus.FAILED
            assert result.error_message == "help", f"Failed for command: {cmd}"

    def test_special_chars_sanitized(self):
        req = make_request("song about <script>alert('xss')</script>")
        result = validate_and_format(req)

        assert "<script>" not in result.formatted_prompt
        assert "alert" in result.formatted_prompt  # Text is kept, tags removed

    def test_whitespace_handling(self):
        req = make_request("   summer vibes   ")
        result = validate_and_format(req)

        assert result.status == JobStatus.VALIDATING


class TestHelpMessage:

    def test_help_message_not_empty(self):
        msg = get_help_message()
        assert len(msg) > 50

    def test_help_message_contains_examples(self):
        msg = get_help_message()
        assert "example" in msg.lower() or "Example" in msg or "pop" in msg.lower()
