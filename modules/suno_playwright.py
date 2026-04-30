import os
import re
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


SUNO_URL = "https://suno.com/create"
PROFILE_DIR = os.path.abspath("chrome_profile")
DOWNLOAD_DIR = os.path.abspath("downloads")


class SunoCreditsError(Exception):
    pass


class SunoPlaywrightBot:
    def __init__(self, headless=False):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=headless,
            accept_downloads=True,
            downloads_path=DOWNLOAD_DIR,
            args=["--disable-blink-features=AutomationControlled"],
        )

        self.page = self.browser.new_page()
        self.page.set_default_timeout(15000)

    def ensure_logged_in(self):
        self.page.goto(SUNO_URL)
        self.page.wait_for_timeout(3000)

        current_url = self.page.url.lower()

        if "/create" in current_url and "login" not in current_url and "sign-in" not in current_url:
            print("✅ Existing Suno session detected.")
            return

        print("⚠️ No valid Suno session found.")
        print("Please log in manually and complete onboarding.")
        input("After Suno create page is fully open, press Enter here...")

        self.page.goto(SUNO_URL)
        self.page.wait_for_timeout(3000)

        if "/create" not in self.page.url.lower():
            raise Exception("Login failed or onboarding incomplete.")

        print("✅ Manual login complete. Session saved.")

    def open_create(self):
        """
        Open Suno create page and retry if Suno redirects to discover/home.
        """
        for attempt in range(3):
            self.page.goto(SUNO_URL)
            self.page.wait_for_timeout(3000)

            current_url = self.page.url.lower()
            print(f"Open create attempt {attempt + 1}: {self.page.url}")

            if "/create" in current_url:
                return

            print(f"Not on create page yet. Retrying... Current URL: {self.page.url}")
            self.page.wait_for_timeout(2000)

        raise Exception(f"Could not open Suno create page. Current URL: {self.page.url}")

    def check_out_of_credits(self):
        """
        Detects both:
        - Out of Credits modal
        - Create button replaced by Out of Credits banner/button
        """
        try:
            body_text = self.page.locator("body").inner_text(timeout=5000)
        except Exception:
            body_text = ""

        lower_text = body_text.lower()

        if "out of credits" not in lower_text and "you're out of credits" not in lower_text:
            return

        refresh_time = self.extract_credit_refresh_time(body_text)

        if refresh_time:
            raise SunoCreditsError(
                f"Suno is out of credits. Credits refresh in {refresh_time}."
            )

        raise SunoCreditsError(
            "Suno is out of credits. Please wait for credits to refresh."
        )

    def extract_credit_refresh_time(self, text):
        """
        Extract timer like:
        1h:39m:21s
        01h:09m:05s
        """
        match = re.search(r"\d+\s*h\s*:\s*\d+\s*m\s*:\s*\d+\s*s", text)
        if match:
            return match.group(0).replace(" ", "")

        return ""

    def find_prompt_box(self):
        textareas = self.page.locator("textarea")
        count = textareas.count()

        print(f"Found {count} textareas")

        for i in range(count):
            box = textareas.nth(i)
            placeholder = box.get_attribute("placeholder") or ""
            visible = box.is_visible()

            print(i, "VISIBLE:", visible, "PLACEHOLDER:", placeholder)

            if not visible:
                continue

            lower_placeholder = placeholder.lower()

            if "lyrics" in lower_placeholder:
                continue

            if "describe the sound" in lower_placeholder:
                continue

            return box

        raise Exception("Could not find visible Suno prompt textarea")

    def get_create_button(self):
        """
        Returns the Create button if present and usable.
        If Suno is out of credits, raises SunoCreditsError.
        """
        self.check_out_of_credits()

        create_button = self.page.locator('button[aria-label="Create song"]')

        if create_button.count() == 0:
            self.check_out_of_credits()
            raise Exception("Create button not found.")

        button = create_button.first

        if not button.is_visible():
            self.check_out_of_credits()
            raise Exception("Create button is not visible.")

        if not button.is_enabled():
            self.check_out_of_credits()
            raise Exception("Create button is disabled.")

        return button

    def generate_song(self, prompt: str) -> str:
        self.open_create()

        print("Current page:", self.page.url)

        # Check BEFORE putting prompt in box
        self.check_out_of_credits()

        prompt_box = self.find_prompt_box()
        prompt_box.click()
        prompt_box.fill(prompt)

        self.page.wait_for_timeout(1000)

        # Check again because Suno may reveal credit state after typing
        self.check_out_of_credits()

        create_button = self.get_create_button()
        create_button.click()

        print("Song generation triggered.")

        # Give Suno time to either start cards or show credits modal/banner
        self.page.wait_for_timeout(5000)

        self.check_out_of_credits()

        # Continue normal generation wait
        self.page.wait_for_timeout(7000)

        return self.wait_and_download_latest_song()

    def wait_and_download_latest_song(self, timeout_sec=420):
        print("Waiting until newest song is downloadable...")

        start = time.time()
        attempt = 1

        while time.time() - start < timeout_sec:
            print(f"\nDownload attempt {attempt}")
            attempt += 1

            try:
                self.check_out_of_credits()
                self.close_open_menus()

                more_button = self.get_newest_song_menu_button()

                if more_button is None:
                    print("No song menu found yet. Waiting...")
                    time.sleep(15)
                    continue

                more_button.click()
                self.page.wait_for_timeout(1000)

                download_item = self.page.get_by_text("Download", exact=True)

                if download_item.count() == 0 or not download_item.first.is_visible():
                    print("Download menu item not visible yet.")
                    self.close_open_menus()
                    time.sleep(15)
                    continue

                print("Hovering Download menu item...")
                download_item.first.hover()
                self.page.wait_for_timeout(1500)

                # If generation is not complete, MP3 may not be enabled/visible.
                mp3_option = self.page.get_by_text("MP3", exact=False)

                if mp3_option.count() == 0 or not mp3_option.first.is_visible():
                    print("MP3 option not visible yet. Song is still processing.")
                    self.close_open_menus()
                    time.sleep(20)
                    continue

                print("MP3 option visible. Starting download...")

                with self.page.expect_download(timeout=20000) as download_info:
                    try:
                        mp3_option.first.click(timeout=5000)
                    except Exception:
                        print("MP3 visible but not clickable yet. Song still processing.")
                        self.close_open_menus()
                        time.sleep(20)
                        continue

                    self.page.wait_for_timeout(1500)

                    download_anyway = self.page.get_by_text("Download Anyway", exact=False)

                    if download_anyway.count() > 0 and download_anyway.first.is_visible():
                        print("Confirmation modal found. Clicking Download Anyway...")
                        download_anyway.first.click()

                download = download_info.value
                filename = f"suno_{int(time.time())}.mp3"
                save_path = os.path.join(DOWNLOAD_DIR, filename)

                download.save_as(save_path)

                print("Downloaded:", save_path)
                return save_path

            except SunoCreditsError:
                raise

            except PlaywrightTimeoutError as e:
                print("Timeout while checking download. Not ready yet:", e)
                self.close_open_menus()
                time.sleep(20)

            except Exception as e:
                print("Not ready yet:", e)
                self.close_open_menus()
                time.sleep(20)

        raise TimeoutError("Song was not downloadable before timeout.")

    def get_newest_song_menu_button(self):
        more_buttons = self.page.locator("button[aria-label*='More']")
        count = more_buttons.count()

        print(f"More buttons found: {count}")

        for i in range(count):
            btn = more_buttons.nth(i)

            try:
                if btn.is_visible() and btn.is_enabled():
                    return btn
            except Exception:
                continue

        return None

    def close_open_menus(self):
        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(500)
        except Exception:
            pass

    def close(self):
        try:
            self.browser.close()
        finally:
            self.playwright.stop()


def create_song_from_prompt(prompt, headless=False):
    bot = SunoPlaywrightBot(headless=headless)

    try:
        bot.ensure_logged_in()
        return bot.generate_song(prompt)

    finally:
        bot.close()


if __name__ == "__main__":
    bot = SunoPlaywrightBot(headless=False)

    try:
        bot.ensure_logged_in()
        file_path = bot.generate_song("a happy pop song about coding")
        print("Final downloaded file:", file_path)

    finally:
        bot.close()