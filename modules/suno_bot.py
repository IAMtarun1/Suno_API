"""
Suno Bot — Selenium Automation for Song Generation.

Owner: V (Vivek)

Responsibility:
    - Login to Suno (via cookies or manual credentials)
    - Submit song generation prompts
    - Wait for and download generated MP3 files
    - Handle anti-bot detection countermeasures
"""

import os
import glob
import time
import random
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from modules.session_manager import save_cookies, load_cookies
from config import selectors
from config.settings import DOWNLOAD_DIR, GENERATION_TIMEOUT_SEC, POLL_INTERVAL_SEC

logger = logging.getLogger(__name__)


class SunoBot:
    """
    Selenium-based automation for Suno music generation.

    Usage:
        bot = SunoBot()
        bot.login()
        file_path = bot.generate_song("a happy pop song about coding")
        bot.cleanup()
    """

    def __init__(self, headless: bool = False):
        """
        Initialize Chrome WebDriver with anti-detection settings.

        Args:
            headless: Run Chrome in headless mode (no visible window).
                      Set to False for debugging, True for production.
        """
        options = webdriver.ChromeOptions()

        # ── Anti-detection flags ────────────────────────────────
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-infobars")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # ── Download settings ───────────────────────────────────
        prefs = {
            "download.default_directory": os.path.abspath(DOWNLOAD_DIR),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        }
        options.add_experimental_option("prefs", prefs)

        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")

        # ── Launch browser ──────────────────────────────────────
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 20)

        # Remove webdriver flag from navigator
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        logger.info("SunoBot initialized")

    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Add a random delay to mimic human behavior."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def login(self) -> bool:
        """
        Login to Suno — tries saved cookies first, falls back to credentials.

        Strategy:
            1. Navigate to Suno
            2. Try loading saved cookies and refreshing
            3. If cookies work → done
            4. If not → attempt credential-based login
            5. Save cookies on success

        Returns:
            True if login was successful
        """
        logger.info("Attempting Suno login...")
        self.driver.get(selectors.SUNO_URL)
        self._random_delay(2, 4)

        # ── Try cookie-based login ──────────────────────────────
        if load_cookies(self.driver):
            self.driver.refresh()
            self._random_delay(3, 5)
            if self._is_logged_in():
                logger.info("✅ Logged in via saved cookies")
                return True
            else:
                logger.info("Saved cookies expired — trying credentials")

        # ── Credential-based login ──────────────────────────────
        try:
            self.driver.get(selectors.LOGIN_URL)
            self._random_delay(2, 3)

            # NOTE: V must update these selectors after inspecting Suno's login page.
            # If Suno uses OAuth (Google/Discord), this section needs to be replaced
            # with a manual-login-once approach:
            #   1. Comment out this section
            #   2. Add input("Login manually, then press Enter...")
            #   3. Call save_cookies(self.driver) after manual login

            email_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors.EMAIL_INPUT))
            )
            email_input.clear()
            email_input.send_keys(os.getenv("SUNO_EMAIL", ""))
            self._random_delay()

            password_input = self.driver.find_element(
                By.CSS_SELECTOR, selectors.PASSWORD_INPUT
            )
            password_input.clear()
            password_input.send_keys(os.getenv("SUNO_PASSWORD", ""))
            self._random_delay()

            login_btn = self.driver.find_element(
                By.CSS_SELECTOR, selectors.LOGIN_BUTTON
            )
            login_btn.click()
            self._random_delay(4, 6)

            if self._is_logged_in():
                save_cookies(self.driver)
                logger.info("✅ Logged in via credentials")
                return True
            else:
                logger.error("Login failed — not detected as logged in")
                return False

        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            return False

    def manual_login(self):
        """
        Open Suno login page and wait for manual login.

        BACKUP STRATEGY: Use this if automated login doesn't work.
        The user logs in manually in the browser window, then
        cookies are saved for future automated sessions.
        """
        self.driver.get(selectors.LOGIN_URL)
        print("\n" + "=" * 60)
        print("MANUAL LOGIN REQUIRED")
        print("Please log in to Suno in the browser window.")
        print("After logging in, press Enter here to continue...")
        print("=" * 60 + "\n")
        input()
        save_cookies(self.driver)
        logger.info("✅ Manual login completed, cookies saved")

    def _is_logged_in(self) -> bool:
        """Check if the user is currently logged in to Suno."""
        try:
            self.driver.find_element(By.CSS_SELECTOR, selectors.LOGGED_IN_INDICATOR)
            return True
        except Exception:
            # Fallback: check if we can access the create page
            try:
                self.driver.find_element(By.CSS_SELECTOR, selectors.CREATE_NAV_LINK)
                return True
            except Exception:
                return False

    def generate_song(self, prompt: str) -> str:
        """
        Submit a prompt to Suno and download the generated song.

        Args:
            prompt: The formatted prompt text to submit

        Returns:
            File path to the downloaded MP3

        Raises:
            TimeoutError: If generation exceeds timeout
            Exception: If any step fails
        """
        logger.info(f"Generating song for prompt: '{prompt[:60]}'")

        # ── Navigate to create page ─────────────────────────────
        self.driver.get(selectors.CREATE_URL)
        self._random_delay(2, 4)

        # ── Enter prompt ────────────────────────────────────────
        textarea = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, selectors.PROMPT_TEXTAREA)
            )
        )
        textarea.clear()
        self._random_delay(0.5, 1.0)

        # Type character by character to mimic human input
        for char in prompt:
            textarea.send_keys(char)
            time.sleep(random.uniform(0.02, 0.08))
        self._random_delay(1, 2)

        # ── Click generate ──────────────────────────────────────
        gen_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, selectors.GENERATE_BUTTON)
            )
        )
        gen_btn.click()
        logger.info("Generate button clicked — waiting for song...")
        self._random_delay(2, 3)

        # ── Wait for download ───────────────────────────────────
        file_path = self._wait_for_download()
        logger.info(f"✅ Song downloaded: {file_path}")
        return file_path

    def _wait_for_download(self) -> str:
        """
        Poll the downloads directory for a new MP3 file.

        Returns:
            Path to the newest MP3 file

        Raises:
            TimeoutError: If no file appears within timeout
        """
        # Record existing files before generation
        existing_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp3")))
        start = time.time()

        while time.time() - start < GENERATION_TIMEOUT_SEC:
            current_files = set(glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp3")))
            new_files = current_files - existing_files

            if new_files:
                # Return the newest new file
                newest = max(new_files, key=os.path.getctime)

                # Wait a moment to ensure download is complete
                time.sleep(2)
                return newest

            elapsed = int(time.time() - start)
            if elapsed % 15 == 0 and elapsed > 0:
                logger.info(f"Still waiting for song... ({elapsed}s elapsed)")

            time.sleep(POLL_INTERVAL_SEC)

        raise TimeoutError(
            f"Song generation timed out after {GENERATION_TIMEOUT_SEC}s"
        )

    def cleanup(self):
        """Close the browser and clean up resources."""
        try:
            self.driver.quit()
            logger.info("SunoBot browser closed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
