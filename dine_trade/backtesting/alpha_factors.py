"""Alpha factor research utilities.

Phase 10.6:
    - Systematic testing of quantitative signals for predictive power.
    - compute_factor_ic(factor_values, forward_returns, horizon_days=5) -> float
    - factor_decay_analysis(factor_df, max_days=20) -> pd.DataFrame

This module is intentionally generic. It doesn't fetch fundamentals itself;
instead, it operates on pandas Series/DataFrames of factor scores and returns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd


@dataclass
class ICResult:
    """Container for information coefficient results."""

    horizon_days: int
    ic: float
    n: int


def compute_factor_ic(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    horizon_days: int = 5,
) -> float:
    """Compute Information Coefficient (IC) between factor and forward returns.

    Both inputs should be 1D pandas Series indexed by a common key
    (e.g. symbol for a single date, or (date, symbol) MultiIndex).

    Steps:
        1. Align factor_values and forward_returns on their index intersection.
        2. Rank both Series (cross-sectional ranking).
        3. Compute Pearson correlation between ranks.

    A value of:
        - > 0.05 suggests statistically meaningful positive predictive power.
        - < -0.05 suggests negative predictive power (contrarian).
    """
    if factor_values is None or forward_returns is None:
        return float("nan")

    x = factor_values.astype(float)
    y = forward_returns.astype(float)

    # Align and drop NaNs
    x, y = x.align(y, join="inner")
    mask = x.notna() & y.notna()
    x = x[mask]
    y = y[mask]

    if len(x) < 3:
        return float("nan")

    # Cross-sectional ranks
    x_rank = x.rank(method="average")
    y_rank = y.rank(method="average")

    # Pearson correlation of ranks (Spearman-style)
    ic = np.corrcoef(x_rank.values, y_rank.values)[0, 1]
    return float(ic)


def factor_decay_analysis(
    factor_df: pd.DataFrame,
    max_days: int = 20,
) -> pd.DataFrame:
    """Analyze how quickly a factor's predictive power decays over time.

    Parameters
    ----------
    factor_df:
        DataFrame with at least two columns:
            - 'factor': factor score at time t
            - 'returns': realized 1-day returns at time t
        Indexed by date (or datetime). This function treats the series as a
        time series for a *single* asset or a cross-sectional average.

    max_days:
        Maximum forward horizon (in days) to test. For each h in [1, max_days],
        the function computes:
            forward_returns_h = returns.shift(-h)
            IC_h = compute_factor_ic(factor_df['factor'], forward_returns_h, h)

    Returns
    -------
    pd.DataFrame
        Columns:
            - 'horizon_days': int
            - 'ic': float
            - 'n': number of observations used
    """
    if "factor" not in factor_df.columns or "returns" not in factor_df.columns:
        raise ValueError("factor_df must contain 'factor' and 'returns' columns")

    results: list[Tuple[int, float, int]] = []
    factor_series = factor_df["factor"]
    ret_series = factor_df["returns"]

    for h in range(1, max_days + 1):
        fwd = ret_series.shift(-h)
        # Align and drop NaNs for this horizon
        x = factor_series.astype(float)
        y = fwd.astype(float)
        x, y = x.align(y, join="inner")
        mask = x.notna() & y.notna()
        x_h = x[mask]
        y_h = y[mask]
        n = len(x_h)
        if n < 3:
            ic = float("nan")
        else:
            # Use compute_factor_ic for consistency
            ic = compute_factor_ic(x_h, y_h, horizon_days=h)
        results.append((h, ic, n))

    df = pd.DataFrame(results, columns=["horizon_days", "ic", "n"])
    return df

