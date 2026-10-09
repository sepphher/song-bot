import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
PLAYLIST_BOT_TOKEN = os.environ["PLAYLIST_BOT_TOKEN"]
PLAYLIST_BOT_USERNAME = os.environ["PLAYLIST_BOT_USERNAME"].lstrip("@")
AUDD_TOKEN = os.getenv("AUDD_TOKEN", "")
COOKIES_KEY = os.getenv("COOKIES_KEY", "")
COOKIES_ENC = os.getenv("COOKIES_ENC", "data/cookies.enc")
BACKUP_KEY = os.getenv("BACKUP_KEY", "")
BACKUP_CHAT_ID = os.getenv("BACKUP_CHAT_ID", "")
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
