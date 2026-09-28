import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
PORT = int(os.getenv("PORT", "8000"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

ROOT = Path(__file__).parent
UPLOADS = ROOT / "uploads"
MUSIC_DIR = ROOT / "static" / "music"
DB_PATH = ROOT / "data.db"
UPLOADS.mkdir(exist_ok=True)
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

# kalit -> botdagi nomi (CSS dagi data-theme bilan bir xil bo'lishi kerak)
THEMES = {
    "oltin": "🌿 Zumrad va oltin",
    "lola": "🌷 Lola",
    "kecha": "🌙 Kechasi",
    "rangli": "🎈 Rangli",
}
