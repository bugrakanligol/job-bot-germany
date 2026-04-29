import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
CV_PATH = DATA_DIR / "cv.pdf"
DB_PATH = ROOT_DIR / "jobs.db"

load_dotenv(ROOT_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

SCORING_CHUNK_SIZE = 10  # jobs per API call

SCORE_THRESHOLD = 70

JOB_KEYWORDS = [
    "Supply Chain",
    "Logistics",
    "Operations",
    "Logistik",
    "Beschaffung",
    "Einkauf",
    "Warehouse",
    "Lager",
    "Procurement",
    "Operations Manager",
    "Lieferkette",
]

LOCATIONS = ["Deutschland", "Germany", "Remote"]

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
