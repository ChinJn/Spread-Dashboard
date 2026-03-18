# transform.py
# ─────────────────────────────────────────────────────────────────────────────
# All data cleaning, spread calculations, and aggregation logic lives here.
# dashboard.py calls these functions; it never does math itself.
# ─────────────────────────────────────────────────────────────────────────────

import pandas as pd
import numpy as np
from config import DISPLAY_TIMEZONE


# ── 1. Clean & enrich raw data ────────────────────────────────────────────────
def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Drop obviously bad rows (zero bid/ask, missing provider/symbol)
    - Convert ms timestamp → UTC datetime → local timezone
    - Add hour / date columns for time-series grouping
    """
    df = df.copy()

    # Drop rows with null essentials
    df.dropna(subset=["provider", "symbol", "bid", "ask", "ts_ms"], inplace=True)

    # Ensure numeric types
    for col in ["bid", "ask", "size", "digits", "ts_ms"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows where bid or ask is non-positive
    df = df[(df["bid"] > 0) & (df["ask"] > 0)]

    # ── Timestamp conversion ─────────────────────────────────────────────────
    # ts_ms is Unix milliseconds → convert to UTC datetime
    df["datetime_utc"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)

    if DISPLAY_TIMEZONE:
        df["datetime"] = df["datetime_utc"].dt.tz_convert(DISPLAY_TIMEZONE)
    else:
        df["datetime"] = df["datetime_utc"]

    # Convenience columns for grouping
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour

    return df.reset_index(drop=True)


# ── 2. Per-row spread calculations ───────────────────────────────────────────
def add_spread_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds three columns to the row-level dataframe:
        spread       — raw decimal spread (ask − bid)
        spread_pips  — spread expressed in pips
        notional     — size × spread (numerator for weighted avg spread)
    """
    df = df.copy()

    # Raw spread
    df["spread"] = df["ask"] - df["bid"]

    # Spread in pips: multiply by 10^digits
    # Clamp digits between 0 and 8 to avoid explosions on bad data
    safe_digits = df["digits"].clip(0, 8).fillna(5).astype(int)
    df["spread_pips"] = df["spread"] * (10 ** safe_digits)

    # Notional value used for weighted-average spread
    df["notional"] = df["spread"] * df["size"]

    return df


# ── 3. Aggregate by provider + symbol ─────────────────────────────────────────
def agg_by_provider_symbol(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per (provider, symbol) with KPI columns:
        weighted_avg_spread, min_spread, max_spread, avg_spread,
        total_volume, trade_count
    """
    grp = df.groupby(["provider", "symbol"])

    agg = grp.apply(
        lambda g: pd.Series({
            "weighted_avg_spread": (
                g["notional"].sum() / g["size"].sum()
                if g["size"].sum() > 0 else np.nan
            ),
            "min_spread":   g["spread"].min(),
            "max_spread":   g["spread"].max(),
            "avg_spread":   g["spread"].mean(),
            "total_volume": g["size"].sum(),
            "trade_count":  len(g),
        })
    ).reset_index()

    return agg


# ── 4. Aggregate by provider only (for bar chart ranking) ────────────────────
def agg_by_provider(df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby("provider")
    agg = grp.apply(
        lambda g: pd.Series({
            "weighted_avg_spread": (
                g["notional"].sum() / g["size"].sum()
                if g["size"].sum() > 0 else np.nan
            ),
            "avg_spread":   g["spread"].mean(),
            "total_volume": g["size"].sum(),
            "trade_count":  len(g),
        })
    ).reset_index()
    return agg.sort_values("weighted_avg_spread")


# ── 5. Spread over time (for line chart) ─────────────────────────────────────
def spread_over_time(df: pd.DataFrame, freq: str = "1h") -> pd.DataFrame:
    """
    Resample spread data to a given frequency.
    freq examples: '15min', '1h', '4h', '1D'
    Returns a DataFrame indexed by datetime with avg / weighted spread.
    """
    df = df.copy()
    df = df.set_index("datetime").sort_index()

    def wagg(g):
        vol = g["size"].sum()
        was = g["notional"].sum() / vol if vol > 0 else np.nan
        return pd.Series({
            "weighted_avg_spread": was,
            "avg_spread": g["spread"].mean(),
            "total_volume": vol,
        })

    ts = df.resample(freq).apply(wagg).reset_index()
    return ts


# ── 6. Heatmap: provider × hour ──────────────────────────────────────────────
def heatmap_provider_hour(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a pivot table:
        rows    = provider
        columns = hour (0–23)
        values  = weighted_avg_spread
    """
    grp = df.groupby(["provider", "hour"]).apply(
        lambda g: pd.Series({
            "weighted_avg_spread": (
                g["notional"].sum() / g["size"].sum()
                if g["size"].sum() > 0 else np.nan
            )
        })
    ).reset_index()

    pivot = grp.pivot(index="provider", columns="hour",
                      values="weighted_avg_spread")
    return pivot


# ── 7. Aggregate by hour ─────────────────────────────────────────────────────
def agg_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per hour (0–23) with spread KPIs.
    """
    grp = df.groupby("hour")
    agg = grp.apply(
        lambda g: pd.Series({
            "weighted_avg_spread": (
                g["notional"].sum() / g["size"].sum()
                if g["size"].sum() > 0 else np.nan
            ),
            "avg_spread":   g["spread"].mean(),
            "min_spread":   g["spread"].min(),
            "max_spread":   g["spread"].max(),
            "total_volume": g["size"].sum(),
            "trade_count":  len(g),
        })
    ).reset_index()
    return agg.sort_values("hour")


# ── 8. Global KPIs (for KPI card row) ────────────────────────────────────────
def compute_kpis(df: pd.DataFrame) -> dict:
    vol = df["size"].sum()
    return {
        "weighted_avg_spread": (
            df["notional"].sum() / vol if vol > 0 else 0
        ),
        "min_spread":    df["spread"].min(),
        "max_spread":    df["spread"].max(),
        "avg_spread":    df["spread"].mean(),
        "total_volume":  vol,
        "trade_count":   len(df),
        "provider_count": df["provider"].nunique(),
        "symbol_count":   df["symbol"].nunique(),
    }
