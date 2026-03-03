"""Verify Alpaca connector: NVDA 100-day OHLCV fetch and get_latest_price. Run from project root."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from dine_trade.config.settings import APCA_API_KEY_ID, APCA_API_SECRET_KEY
from dine_trade.data.connectors.alpaca_connector import DATA_API_BASE, get_ohlcv, get_latest_price

def main():
    symbol = "NVDA"
    # Safe credential check (no values printed)
    key_ok = bool((APCA_API_KEY_ID or "").strip())
    secret_ok = bool((APCA_API_SECRET_KEY or "").strip())
    print(f"Data API base: {DATA_API_BASE}")
    print(f"APCA_API_KEY_ID: {'set (' + str(len((APCA_API_KEY_ID or '').strip())) + ' chars)' if key_ok else 'NOT SET or empty'}")
    print(f"APCA_API_SECRET_KEY: {'set (' + str(len((APCA_API_SECRET_KEY or '').strip())) + ' chars)' if secret_ok else 'NOT SET or empty'}")
    if not key_ok or not secret_ok:
        print()
        print("  In .env use exactly (no quotes, no spaces around =):")
        print("  APCA_API_KEY_ID=<your Key from Alpaca dashboard>")
        print("  APCA_API_SECRET_KEY=<your Secret from Alpaca dashboard>")
        print("  APCA_API_BASE_URL=https://paper-api.alpaca.markets")
        return 1
    print(f"Fetching {symbol} OHLCV (100 days)...")
    try:
        df = get_ohlcv(symbol, days=100)
    except Exception as e:
        print(f"  Connection error: {e}")
        print("  401 = bad credentials; 403 = use feed=iex (free tier). Re-copy keys if needed; no quotes in .env.")
        return 1
    print(f"  Shape: {df.shape}")
    if df.empty:
        print("  WARNING: No bars returned (check Alpaca API keys and data subscription).")
        return 1
    print(f"  Columns: {list(df.columns)}")
    print(f"  Last row: date={df.iloc[-1]['date']}, close={df.iloc[-1]['close']}")
    print()
    print(f"get_latest_price({symbol!r})...")
    price = get_latest_price(symbol)
    print(f"  Result: {price}")
    if price is None:
        print("  WARNING: No price (quote or bars).")
        return 1
    print("  OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
