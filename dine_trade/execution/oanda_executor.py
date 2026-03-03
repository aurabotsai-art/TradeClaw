import json
from typing import Any, Dict, List

import requests

from dine_trade.config.settings import (
    OANDA_ACCOUNT_ID,
    OANDA_API_KEY,
    OANDA_ENVIRONMENT,
)


class OandaConfigError(RuntimeError):
    pass


def _base_url() -> str:
    env = (OANDA_ENVIRONMENT or "practice").lower()
    if env == "live":
        return "https://api-fxtrade.oanda.com"
    return "https://api-fxpractice.oanda.com"


def _headers() -> Dict[str, str]:
    api_key = (OANDA_API_KEY or "").strip()
    if not api_key or not OANDA_ACCOUNT_ID:
        raise OandaConfigError(
            "OANDA_API_KEY and OANDA_ACCOUNT_ID must be set in the environment."
        )
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def place_limit_order(
    instrument: str,
    units: float,
    price: float,
    stop_loss: float,
    take_profit: float,
) -> Dict[str, Any]:
    """
    Place an OANDA LIMIT order with mandatory stopLossOnFill and takeProfitOnFill.

    Units: positive = buy, negative = sell.
    """
    url = f"{_base_url()}/v3/accounts/{OANDA_ACCOUNT_ID}/orders"

    order = {
        "type": "LIMIT",
        "instrument": instrument,
        "units": str(int(units)),
        "price": f"{price:.5f}",
        "timeInForce": "GTC",
        "positionFill": "DEFAULT",
        "stopLossOnFill": {"price": f"{stop_loss:.5f}"},
        "takeProfitOnFill": {"price": f"{take_profit:.5f}"},
    }

    payload = {"order": order}

    resp = requests.post(url, headers=_headers(), data=json.dumps(payload), timeout=10)
    try:
        data = resp.json()
    except json.JSONDecodeError:
        resp.raise_for_status()
        raise

    if not resp.ok:
        # Surface OANDA error details to caller
        raise RuntimeError(f"OANDA order error: {resp.status_code} {data}")

    return data


def get_open_trades() -> List[Dict[str, Any]]:
    """
    Fetch all open trades for the configured OANDA account.
    Useful for hedge-ratio calculations and rebalancing.
    """
    url = f"{_base_url()}/v3/accounts/{OANDA_ACCOUNT_ID}/openTrades"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("trades", [])

