
import os
from pathlib import Path
from dotenv import load_dotenv

# Find project root:
# Enterprise-Sales-Enterprise/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Explicitly load .env from project root
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_FILE)

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Validate configuration
required_settings = {
    "DB_NAME": DB_NAME,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}

missing_settings = [
    key for key, value in required_settings.items()
    if not value
]

if missing_settings:
    raise ValueError(
        f"Missing database settings: {missing_settings}. "
        f"Check your .env file at {ENV_FILE}"
    )

print("Database configuration loaded successfully!")