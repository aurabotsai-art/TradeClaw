"""Order Book Imbalance (OBI) utilities.

compute_obi(order_book: dict, depth=10) -> float

    OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol)

Where:
    - bid_vol = sum of bid quantities over top N levels
    - ask_vol = sum of ask quantities over top N levels
    - Range: -1.0 (strong sell pressure) to +1.0 (strong buy pressure)

obi_signal(obi: float, threshold=0.3) -> str

    >  threshold  -> "BULLISH_PRESSURE"
    < -threshold  -> "BEARISH_PRESSURE"
    else          -> "NEUTRAL"

Order book shape expectations:
    {
        "bids": [(price, size), ...]  # or [["price", "size"], ...]
        "asks": [(price, size), ...]
    }

For crypto: upstream code should feed Binance depth WS into this format.
For equities: upstream code should feed Polygon Level 2 depth into this format.
"""

from __future__ import annotations

from typing import Iterable, Sequence, Tuple


def _sum_depth(levels: Iterable[Sequence[float]], depth: int) -> float:
    """Sum size over top N levels, ignoring malformed entries."""
    total = 0.0
    n = 0
    for level in levels:
        if n >= depth:
            break
        if len(level) < 2:
            continue
        try:
            size = float(level[1])
        except (TypeError, ValueError):
            continue
        total += size
        n += 1
    return total


def compute_obi(order_book: dict, depth: int = 10) -> float:
    """Compute order book imbalance (OBI) for the top N levels.

    OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol)
    """
    bids = order_book.get("bids") or []
    asks = order_book.get("asks") or []

    bid_vol = _sum_depth(bids, depth)
    ask_vol = _sum_depth(asks, depth)

    denom = bid_vol + ask_vol
    if denom <= 0:
        return 0.0

    obi = (bid_vol - ask_vol) / denom
    # Clamp to [-1.0, 1.0] for safety
    if obi > 1.0:
        return 1.0
    if obi < -1.0:
        return -1.0
    return float(obi)


def obi_signal(obi: float, threshold: float = 0.3) -> str:
    """Map OBI value to a discrete signal."""
    if obi > threshold:
        return "BULLISH_PRESSURE"
    if obi < -threshold:
        return "BEARISH_PRESSURE"
    return "NEUTRAL"

