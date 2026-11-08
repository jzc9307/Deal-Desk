"""Read settings and private keys when the server starts."""
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Read the local .env file. Settings already supplied by the host take priority.
# On Render, enter private keys in Environment rather than putting them in Git.
load_dotenv(BASE_DIR / ".env", override=False)

# Local checks and calculations can still run if no Gemini key is loaded.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
# Comma-separated keys OR numbered backups, e.g. GEMINI_API_KEY_2.
# Never print these keys or send them to the browser.
GEMINI_API_KEYS = tuple(dict.fromkeys(key.strip() for key in [
    GEMINI_API_KEY,
    *(os.environ[name] for name in sorted(
        (name for name in os.environ if name.startswith('GEMINI_API_KEY_')
         and name.removeprefix('GEMINI_API_KEY_').isdigit()),
        key=lambda name: int(name.removeprefix('GEMINI_API_KEY_')))),
    *os.environ.get("GEMINI_API_KEYS", "").split(","),
] if key.strip()))
CHEAP_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")
GEMINI_THINKING_LEVEL = os.environ.get('GEMINI_THINKING_LEVEL', 'low').strip().lower()
if GEMINI_THINKING_LEVEL not in {'low', 'medium', 'high'}:
    raise ValueError('GEMINI_THINKING_LEVEL must be low, medium, or high.')
AI_ANALYSIS_TIMEOUT_MS = max(10000, min(60000, int(os.environ.get('AI_ANALYSIS_TIMEOUT_MS', '60000'))))
# Give photo recognition its own timeout; the shorter chat timeout is not enough.
AI_VISION_TIMEOUT_MS = max(10000, min(60000, int(os.environ.get('AI_VISION_TIMEOUT_MS', '60000'))))
# Primary and fallback attempts share this time; a retry does not reset it.
AI_CALL_TOTAL_TIMEOUT_MS = max(10000, min(60000, int(os.environ.get('AI_CALL_TOTAL_TIMEOUT_MS', '45000'))))
AI_PRIMARY_ATTEMPT_TIMEOUT_MS = max(5000, min(30000, int(os.environ.get('AI_PRIMARY_ATTEMPT_TIMEOUT_MS', '20000'))))
AI_MODEL_COOLDOWN_SECONDS = max(30, int(os.environ.get('AI_MODEL_COOLDOWN_SECONDS', '300')))
SEARCH_TIMEOUT_SECONDS = max(30, min(120, float(os.environ.get('SEARCH_TIMEOUT_SECONDS', '110'))))
RETRIEVAL_TIMEOUT_SECONDS = max(1, min(45, float(os.environ.get('RETRIEVAL_TIMEOUT_SECONDS', '35'))))
LENS_IMAGE_TIMEOUT_SECONDS = max(1, min(15, float(os.environ.get('LENS_IMAGE_TIMEOUT_SECONDS', '10'))))

# These are our local safety limits, not Google's remaining quota.
# Keys with no project label share one local budget to avoid overcounting.
GEMINI_KEY_PROJECTS = tuple(part.strip() for part in os.environ.get('GEMINI_KEY_PROJECTS', '').split(','))
GEMINI_LOCAL_RPM = max(1, int(os.environ.get('GEMINI_LOCAL_RPM', '5')))
GEMINI_LOCAL_RPD = max(1, int(os.environ.get('GEMINI_LOCAL_RPD', '20')))
GEMINI_MAX_ATTEMPTS = max(1, min(5, int(os.environ.get('GEMINI_MAX_ATTEMPTS', '2'))))
AI_OPERATION_BUDGET = max(1, min(8, int(os.environ.get('AI_OPERATION_BUDGET', '3'))))
AI_SHORTLIST_SIZE = max(1, min(12, int(os.environ.get('AI_SHORTLIST_SIZE', '8'))))
AI_EVIDENCE_TTL = max(60, int(os.environ.get('AI_EVIDENCE_TTL', '3600')))

# Use the Carousell provider if configured. Otherwise try its public search page.
# If a source blocks the request, report that instead of making up results.
REEF_API_KEY = os.environ.get("REEF_API_KEY", "").strip()
REEF_API_BASE = os.environ.get("REEF_API_BASE", "https://api.reefapi.com").rstrip("/")

# Prefer the Shopee search provider when a key is available.
# The public-browser fallback may be blocked by Shopee.
NEXSCOPE_API_KEY = os.environ.get("NEXSCOPE_API_KEY", "").strip()
NEXSCOPE_SHOPEE_URL = os.environ.get(
    "NEXSCOPE_SHOPEE_URL",
    "https://api.nexscope.ai/api/skill-api/v1/skills/shopee-product-search/run",
).strip()

# eBay and Etsy need their own API credentials; a Gemini key cannot access them.
EBAY_CLIENT_ID = os.environ.get("EBAY_CLIENT_ID", "").strip()
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET", "").strip()
EBAY_MARKETPLACE_ID = os.environ.get("EBAY_MARKETPLACE_ID", "EBAY_US").strip()
ETSY_API_KEY = os.environ.get("ETSY_API_KEY", "").strip()
ETSY_SHARED_SECRET = os.environ.get("ETSY_SHARED_SECRET", "").strip()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

# Default filters, shipping assumptions and profit rules.
MAX_PRICE_MYR = float(os.environ.get("MAX_PRICE_MYR", "2500"))
MIN_SELLER_RATING = float(os.environ.get("MIN_SELLER_RATING", "4.0"))
PLATFORM_FEE_PCT = float(os.environ.get("PLATFORM_FEE_PCT", "0.05"))
SHIPPING_COST_MYR = float(os.environ.get("SHIPPING_COST_MYR", "8"))
MIN_MARGIN_PCT_TO_ALERT = float(os.environ.get("MIN_MARGIN_PCT_TO_ALERT", "20"))

MAX_SEARCH_RESULTS = int(os.environ.get("MAX_SEARCH_RESULTS", "12"))
CACHE_PATH = BASE_DIR / "cache" / "listings_raw.json"
