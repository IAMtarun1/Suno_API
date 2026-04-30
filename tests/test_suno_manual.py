from modules.suno_bot import SunoBot

bot = SunoBot(headless=False)

try:
    print("Opening Suno...")
    ok = bot.login()

    if not ok:
        print("Auto-login failed. Starting manual login...")
        bot.manual_login()

    print("Generating test song...")
    file_path = bot.generate_song("a short happy pop song about coding")

    print("Downloaded file:", file_path)

finally:
    bot.cleanup()