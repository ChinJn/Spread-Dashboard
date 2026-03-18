# db.py
# ─────────────────────────────────────────────────────────────────────────────
# Handles database connection and raw data extraction.
# Uses SQLAlchemy (MySQL by default). Swap the connection string for
# PostgreSQL / MSSQL / SQLite as needed.
# ─────────────────────────────────────────────────────────────────────────────

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from config import COLUMNS, TABLE_NAME

load_dotenv()   # reads .env file

# ── Build connection string ───────────────────────────────────────────────────
def _get_engine():
    """Create and return a SQLAlchemy engine from .env credentials."""
    host     = os.getenv("DB_HOST", "localhost")
    port     = os.getenv("DB_PORT", "3306")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    db_name  = os.getenv("DB_NAME")

    # MySQL / MariaDB  →  mysql+pymysql://
    # PostgreSQL       →  postgresql+psycopg2://
    # MS SQL Server    →  mssql+pyodbc://?driver=ODBC+Driver+17+for+SQL+Server
    conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(conn_str, pool_pre_ping=True)


# ── SQL query template ────────────────────────────────────────────────────────
def build_query(date_from: str, date_to: str) -> str:
    """
    Returns a parameterized SQL query string.

    date_from / date_to: 'YYYY-MM-DD' strings used to filter by timestamp.
    Adjust the WHERE clause if your timestamp column is already a DATETIME
    rather than milliseconds.
    """
    c = COLUMNS      # shorthand alias

    # Convert the ms timestamp boundaries to Unix ms integers
    # so we can filter in the SQL layer before pulling rows.
    sql = f"""
        SELECT
            `{c['provider']}`   AS provider,
            `{c['symbol']}`     AS symbol,
            `{c['bid']}`        AS bid,
            `{c['ask']}`        AS ask,
            `{c['size']}`       AS size,
            `{c['digits']}`     AS digits,
            `{c['timestamp']}`  AS ts_ms
            -- OPTIONAL columns (uncomment if available in your schema):
            -- ,`{c['markup']}`   AS markup
            -- ,`{c['fill_price']}` AS fill_price
        FROM  `{TABLE_NAME}`
        WHERE
            `{c['timestamp']}` >= UNIX_TIMESTAMP(:date_from) * 1000
            AND `{c['timestamp']}` <  UNIX_TIMESTAMP(:date_to)  * 1000
            AND `{c['bid']}`  > 0
            AND `{c['ask']}`  > 0
        ORDER BY `{c['timestamp']}` ASC
    """
    return sql


# ── Main fetch function ───────────────────────────────────────────────────────
def fetch_data(date_from: str, date_to: str) -> pd.DataFrame:
    """
    Pull raw spread data from the database for the given date range.

    Parameters
    ----------
    date_from : str  — e.g. '2024-01-01'
    date_to   : str  — e.g. '2024-01-31'

    Returns
    -------
    pd.DataFrame with standardised column names ready for transform.py
    """
    engine = _get_engine()
    query  = build_query(date_from, date_to)

    with engine.connect() as conn:
        df = pd.read_sql(
            text(query),
            conn,
            params={"date_from": date_from, "date_to": date_to},
        )

    return df


# ── Demo / offline fallback (used when no DB is available) ───────────────────
def fetch_sample_data() -> pd.DataFrame:
    """
    Generates synthetic data so the dashboard works without a live DB.
    Remove or disable this once you have a real connection.
    """
    import numpy as np
    rng = np.random.default_rng(42)

    n = 5_000
    providers = ["LP_Alpha", "LP_Beta", "LP_Gamma", "LP_Delta", "LP_Epsilon"]
    symbols   = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]
    digits_map = {"EURUSD": 5, "GBPUSD": 5, "USDJPY": 3,
                  "XAUUSD": 2, "BTCUSD": 2}

    sym  = rng.choice(symbols,    n)
    prov = rng.choice(providers,  n)
    mid  = rng.uniform(1.05, 1.15, n)  # synthetic mid price

    # Vary spread width by provider to make the demo interesting
    provider_spread_factor = {
        "LP_Alpha": 0.3, "LP_Beta": 0.8, "LP_Gamma": 0.5,
        "LP_Delta": 1.2, "LP_Epsilon": 0.6
    }
    half_spread = rng.uniform(0.00005, 0.0003, n) * \
                  [provider_spread_factor[p] for p in prov]

    bid  = mid - half_spread
    ask  = mid + half_spread
    size = rng.uniform(0.1, 10.0, n).round(2)

    # Timestamps: last 30 days in ms
    base_ts = int(pd.Timestamp("2024-01-01").timestamp() * 1000)
    ts_ms   = base_ts + rng.integers(0, 30 * 24 * 3600 * 1000, n)

    df = pd.DataFrame({
        "provider": prov,
        "symbol":   sym,
        "bid":      bid,
        "ask":      ask,
        "size":     size,
        "digits":   [digits_map[s] for s in sym],
        "ts_ms":    ts_ms,
    })
    return df
