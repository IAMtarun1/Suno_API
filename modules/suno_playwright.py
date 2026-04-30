import os
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

        if "login" not in current_url and "sign-in" not in current_url and "/create" in current_url:
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
        self.page.goto(SUNO_URL)
        self.page.wait_for_timeout(3000)

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

    def check_out_of_credits(self):
        """
        Detect Suno paywall / out-of-credits modal.
        """
        try:
            out_of_credits = self.page.get_by_text("Out of Credits", exact=False)

            if out_of_credits.count() > 0 and out_of_credits.first.is_visible():
                raise SunoCreditsError(
                    "Suno account is out of credits."
                )

        except Exception:
            return

    def generate_song(self, prompt: str) -> str:
        self.open_create()

        print("Current page:", self.page.url)

        prompt_box = self.find_prompt_box()
        prompt_box.click()
        prompt_box.fill(prompt)

        self.page.wait_for_timeout(1000)

        create_button = self.page.locator('button[aria-label="Create song"]')
        create_button.wait_for(state="visible", timeout=10000)

        if not create_button.is_enabled():
            raise Exception("Create button is disabled after filling prompt.")

        create_button.click()
        print("Song generation triggered.")

        # Wait a few seconds for Suno to either begin generation or show credit modal
        self.page.wait_for_timeout(4000)

        # Detect paywall
        self.check_out_of_credits()

        # Continue normal wait
        self.page.wait_for_timeout(8000)

    def wait_and_download_latest_song(self, timeout_sec=420):
        print("Waiting until newest song is downloadable...")

        start = time.time()
        attempt = 1

        while time.time() - start < timeout_sec:
            print(f"\nDownload attempt {attempt}")
            attempt += 1

            try:
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

                # Download is a hover menu. If song is still processing,
                # MP3 / WAV / Video will NOT appear.
                print("Hovering Download menu item...")
                download_item.first.hover()
                self.page.wait_for_timeout(1500)

                mp3_option = self.page.get_by_text("MP3", exact=False)

                if mp3_option.count() == 0 or not mp3_option.first.is_visible():
                    print("MP3 option not visible yet. Song is still processing.")
                    self.close_open_menus()
                    time.sleep(20)
                    continue

                print("MP3 option visible. Starting download...")

                with self.page.expect_download(timeout=90000) as download_info:
                    mp3_option.first.click()
                    self.page.wait_for_timeout(1500)

                    # Confirmation modal may appear.
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
        """
        Gets the first visible three-dot menu.
        Suno generally shows newest generated songs at the top of the workspace list.
        """
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