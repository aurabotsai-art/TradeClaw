"""DataValidator (Audit: Data Sanity Check). Required before any trade.
Use e.g. Alpaca bars close vs Alpaca quote mid. Used in Phase 1 script and Executor (Phase 3)."""


def validate_price_agreement(
    price_a: float,
    price_b: float,
    tolerance_pct: float = 0.1,
) -> tuple[bool, str]:
    """Two price sources must agree within tolerance_pct before any trade.
    deviation = |price_a - price_b| / price_b * 100
    Returns (True, "OK") if deviation <= tolerance_pct, else (False, message).
    """
    if price_b <= 0:
        return False, "Reference price (price_b) must be positive"
    if price_a <= 0:
        return False, "Price A must be positive"
    deviation_pct = abs(price_a - price_b) / price_b * 100
    if deviation_pct <= tolerance_pct:
        return True, "OK"
    return False, f"Price deviation {deviation_pct:.4f}% exceeds {tolerance_pct}%"
