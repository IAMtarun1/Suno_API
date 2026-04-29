"""
Centralized Suno DOM selectors.

Owner: V (Vivek)

IMPORTANT: When Suno updates their UI, ONLY this file needs to change.
All Selenium code references these constants instead of hardcoding selectors.

HOW TO UPDATE:
    1. Open Suno in Chrome
    2. Right-click target element → Inspect
    3. Find a stable selector (prefer data-testid, aria-label, or id)
    4. Update the constant below
    5. Run tests to verify
"""

# ─── URLs ───────────────────────────────────────────────────────────
SUNO_URL = "https://suno.com"
LOGIN_URL = "https://suno.com/signin"
CREATE_URL = "https://suno.com/create"

# ─── Login Page Selectors ──────────────────────────────────────────
# NOTE: Suno may use OAuth (Google/Discord). If so, these won't apply.
# V should inspect the actual login page and update accordingly.
EMAIL_INPUT = "input[type='email']"
PASSWORD_INPUT = "input[type='password']"
LOGIN_BUTTON = "button[type='submit']"

# OAuth buttons (if Suno uses OAuth login)
GOOGLE_LOGIN_BUTTON = "button[data-provider='google']"      # Placeholder — inspect and update
DISCORD_LOGIN_BUTTON = "button[data-provider='discord']"    # Placeholder — inspect and update

# ─── Create Page Selectors ─────────────────────────────────────────
# These MUST be updated by inspecting Suno's live create page
PROMPT_TEXTAREA = "textarea"                                 # Placeholder — inspect and update
GENERATE_BUTTON = "button[data-testid='generate']"          # Placeholder — inspect and update
CUSTOM_MODE_TOGGLE = "button[data-testid='custom-mode']"    # Placeholder — inspect and update

# ─── Song Result Selectors ─────────────────────────────────────────
SONG_CARD = ".song-card"                                     # Placeholder — inspect and update
SONG_PLAY_BUTTON = "button[aria-label='play']"              # Placeholder — inspect and update
DOWNLOAD_BUTTON = "button[aria-label='download']"           # Placeholder — inspect and update
SONG_AUDIO_ELEMENT = "audio source"                         # For direct audio URL extraction

# ─── Navigation / State Detection ──────────────────────────────────
# Elements that indicate the user is logged in
LOGGED_IN_INDICATOR = "[data-testid='user-menu']"           # Placeholder — inspect and update
CREATE_NAV_LINK = "a[href='/create']"                       # Placeholder — inspect and update

# ─── Loading / Progress Indicators ─────────────────────────────────
LOADING_SPINNER = ".loading-spinner"                         # Placeholder — inspect and update
GENERATION_PROGRESS = "[data-testid='generation-progress']" # Placeholder — inspect and update
