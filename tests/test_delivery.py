"""
Tests for the Delivery Layer.

Owner: D (Dhir)
"""

import pytest
from unittest.mock import patch, MagicMock
from contracts.interfaces import SongRequest, SongResult, JobStatus


class TestSendSong:

    @patch("modules.delivery.TWILIO_ACCOUNT_SID", "test_sid")
    @patch("modules.delivery.TWILIO_AUTH_TOKEN", "test_token")
    @patch("modules.delivery.Client")
    def test_send_song_success(self, MockClient):
        from modules.delivery import send_song

        mock_client = MockClient.return_value
        mock_message = MagicMock()
        mock_message.sid = "SM123"
        mock_client.messages.create.return_value = mock_message

        req = SongRequest(sender="whatsapp:+1234567890", raw_prompt="test")
        result = SongResult(
            request=req,
            file_path="/tmp/song.mp3",
            media_url="https://example.com/audio/song.mp3",
            generation_time_sec=45.0,
            success=True
        )

        assert send_song(result) is True
        mock_client.messages.create.assert_called_once()

    @patch("modules.delivery.TWILIO_ACCOUNT_SID", "")
    @patch("modules.delivery.TWILIO_AUTH_TOKEN", "")
    def test_send_song_no_credentials(self):
        from modules.delivery import send_song

        req = SongRequest(sender="whatsapp:+1234567890", raw_prompt="test")
        result = SongResult(request=req, success=False)

        assert send_song(result) is False


class TestSendError:

    @patch("modules.delivery.TWILIO_ACCOUNT_SID", "test_sid")
    @patch("modules.delivery.TWILIO_AUTH_TOKEN", "test_token")
    @patch("modules.delivery.Client")
    def test_send_error_valid_type(self, MockClient):
        from modules.delivery import send_error

        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = MagicMock(sid="SM456")

        assert send_error("whatsapp:+1234567890", "invalid_prompt") is True

    @patch("modules.delivery.TWILIO_ACCOUNT_SID", "test_sid")
    @patch("modules.delivery.TWILIO_AUTH_TOKEN", "test_token")
    @patch("modules.delivery.Client")
    def test_send_error_unknown_type_falls_back(self, MockClient):
        from modules.delivery import send_error

        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = MagicMock(sid="SM789")

        # Unknown error type should fall back to generation_failed
        assert send_error("whatsapp:+1234567890", "unknown_error") is True
