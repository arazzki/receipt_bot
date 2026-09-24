import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "db_receipt_bot")

DEFAULT_MARIADB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_MARIADB_URL)

# Fallback SQLite DB path if MariaDB unavailable during dev
SQLITE_FALLBACK_URL = f"sqlite:///{BASE_DIR / 'receipt_bot.db'}"

# Tesseract OCR Configuration
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
OCR_LANG = os.getenv("OCR_LANG", "ind+eng")

# Temp storage
TEMP_DIR = Path(os.getenv("TEMP_DIR", BASE_DIR / "temp"))
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Application Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
