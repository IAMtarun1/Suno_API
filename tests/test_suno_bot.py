"""
Tests for the Suno Bot module.

Owner: V (Vivek)

NOTE: These tests use mocks — they do NOT launch a real browser.
Real browser testing should be done manually during development.
"""

import pytest
from unittest.mock import MagicMock, patch
from modules.session_manager import save_cookies, load_cookies, clear_cookies


class TestSessionManager:

    @patch("modules.session_manager.COOKIE_FILE", "/tmp/test_cookies.json")
    def test_save_and_load_cookies(self):
        """Test the cookie save/load roundtrip."""
        mock_driver = MagicMock()
        mock_driver.get_cookies.return_value = [
            {"name": "session", "value": "abc123", "domain": ".suno.com"}
        ]

        # Save
        result = save_cookies(mock_driver)
        assert result is True

        # Load
        mock_driver2 = MagicMock()
        result = load_cookies(mock_driver2)
        assert result is True
        mock_driver2.add_cookie.assert_called_once()

    @patch("modules.session_manager.COOKIE_FILE", "/tmp/nonexistent_cookies.json")
    def test_load_missing_cookies(self):
        """Loading cookies when no file exists should return False."""
        import os
        if os.path.exists("/tmp/nonexistent_cookies.json"):
            os.remove("/tmp/nonexistent_cookies.json")

        mock_driver = MagicMock()
        result = load_cookies(mock_driver)
        assert result is False

    @patch("modules.session_manager.COOKIE_FILE", "/tmp/test_clear_cookies.json")
    def test_clear_cookies(self):
        """Clearing cookies should remove the file."""
        import os
        # Create a dummy file
        with open("/tmp/test_clear_cookies.json", "w") as f:
            f.write("[]")

        result = clear_cookies()
        assert result is True
        assert not os.path.exists("/tmp/test_clear_cookies.json")
