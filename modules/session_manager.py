"""
Session Manager — Cookie Persistence for Suno Login.

Owner: V (Vivek)

Responsibility:
    - Save browser cookies after successful login
    - Load cookies to restore session without re-authenticating
    - Validate that loaded cookies are still valid

This avoids the need to automate OAuth login flows (Google/Discord),
which are complex and fragile. Instead:
    1. Login manually once in the automated browser
    2. Save cookies
    3. Reuse cookies for subsequent sessions
"""

import json
import os
import logging
from config.settings import COOKIE_FILE

logger = logging.getLogger(__name__)


def save_cookies(driver) -> bool:
    """
    Save all browser cookies to a JSON file.

    Call this after a successful login to persist the session.

    Args:
        driver: Selenium WebDriver instance

    Returns:
        True if cookies were saved successfully
    """
    try:
        cookies = driver.get_cookies()
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
        
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f, indent=2)
        
        logger.info(f"Saved {len(cookies)} cookies to {COOKIE_FILE}")
        return True

    except Exception as e:
        logger.error(f"Failed to save cookies: {e}")
        return False


def load_cookies(driver) -> bool:
    """
    Load cookies from JSON file and inject them into the browser.

    IMPORTANT: The browser must already be on the correct domain
    before loading cookies (navigate to suno.com first).

    Args:
        driver: Selenium WebDriver instance

    Returns:
        True if cookies were loaded successfully
    """
    if not os.path.exists(COOKIE_FILE):
        logger.info("No saved cookies found — fresh login required")
        return False

    try:
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)

        loaded_count = 0
        for cookie in cookies:
            try:
                # Some cookies may have domain mismatches — skip those
                driver.add_cookie(cookie)
                loaded_count += 1
            except Exception as e:
                logger.debug(f"Skipped cookie '{cookie.get('name', '?')}': {e}")

        logger.info(f"Loaded {loaded_count}/{len(cookies)} cookies from {COOKIE_FILE}")
        return loaded_count > 0

    except json.JSONDecodeError:
        logger.error("Cookie file is corrupted — deleting it")
        os.remove(COOKIE_FILE)
        return False

    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
        return False


def clear_cookies() -> bool:
    """
    Delete the saved cookie file.

    Use this when cookies are expired and a fresh login is needed.

    Returns:
        True if the file was deleted (or didn't exist)
    """
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)
        logger.info("Cleared saved cookies")
    return True
