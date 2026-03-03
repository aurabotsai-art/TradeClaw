"""Config and constants: secrets backend first, then os.environ; model hybridization (Pro/Flash).

NEVER commit .env to Git. Production: use AWS Secrets Manager, GCP Secret Manager,
Docker secrets, or HashiCorp Vault; set DINETRADE_SECRETS_BACKEND and backend-specific env.
"""
import os
from dotenv import load_dotenv

from dine_trade.config.secrets import get_secret

load_dotenv()


def _env(key: str, default: str = "") -> str:
    """Prefer secrets backend, then env var."""
    v = get_secret(key)
    if v is not None and v != "":
        return v.strip()
    return os.getenv(key, default).strip()


# --- API keys (secrets or env) ---
GEMINI_API_KEY = _env("GEMINI_API_KEY", "")

# Alpaca (APCA_*)
APCA_API_KEY_ID = _env("APCA_API_KEY_ID", "")
APCA_API_SECRET_KEY = _env("APCA_API_SECRET_KEY", "")
APCA_API_BASE_URL = _env("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

# OANDA (FX/CFD)
OANDA_API_KEY = _env("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = _env("OANDA_ACCOUNT_ID", "")
OANDA_ENVIRONMENT = _env("OANDA_ENVIRONMENT", "practice")  # 'practice' or 'live'

# Data & news (FMP = news; Polygon optional)
FMP_API_KEY = _env("FMP_API_KEY", "")
POLYGON_API_KEY = _env("POLYGON_API_KEY", "")

# Binance (crypto)
BINANCE_API_KEY = _env("BINANCE_API_KEY", "")
BINANCE_API_SECRET = _env("BINANCE_API_SECRET", "")
BINANCE_TESTNET = _env("BINANCE_TESTNET", "false").lower() in ("true", "1", "yes")

# Supabase
SUPABASE_URL = _env("SUPABASE_URL", "")
SUPABASE_KEY = _env("SUPABASE_KEY", "") or _env("SUPABASE_SERVICE_ROLE_KEY", "") or _env("SUPABASE_ANON_KEY", "")

# Pinecone (vector database)
PINECONE_API_KEY = _env("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = _env("PINECONE_INDEX_NAME", "")

# --- Model hybridization ---
GEMINI_MODEL_RESEARCHER = _env("GEMINI_MODEL_RESEARCHER", "gemini-3.1-pro-preview")
GEMINI_MODEL_FAST = _env("GEMINI_MODEL_FAST", "gemini-3-flash-preview")

# --- Constants ---
DAILY_DRAWDOWN_LIMIT_PCT = 1.5
MAX_RISK_PER_TRADE_PCT = 1.0
PAPER_MODE = True
UNIVERSE_DEFAULT = ["NVDA"]
CRYPTO_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

# Override from secrets/env when set
_dd = _env("DAILY_DRAWDOWN_LIMIT_PCT")
if _dd:
    DAILY_DRAWDOWN_LIMIT_PCT = float(_dd)
_risk = _env("MAX_RISK_PER_TRADE_PCT")
if _risk:
    MAX_RISK_PER_TRADE_PCT = float(_risk)
_paper = _env("PAPER_MODE")
if _paper:
    PAPER_MODE = _paper.lower() in ("true", "1", "yes")

# Kill-switch
TRADING_ENABLED = _env("TRADING_ENABLED", "true").lower() == "true"
