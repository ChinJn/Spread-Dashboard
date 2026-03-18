# config.py
# ─────────────────────────────────────────────────────────────────────────────
# Central place to configure column name mappings and app constants.
# If your SQL table uses different column names, only edit this file.
# ─────────────────────────────────────────────────────────────────────────────

# ── Timezone ─────────────────────────────────────────────────────────────────
# Set to None to keep UTC, or e.g. "Asia/Kuala_Lumpur", "Europe/London"
DISPLAY_TIMEZONE = "Asia/Kuala_Lumpur"

# ── SQL table name ────────────────────────────────────────────────────────────
TABLE_NAME = "deals"           # Change to your actual table name

# ── Column name mappings ──────────────────────────────────────────────────────
# Left  = internal name used throughout the project (do NOT change)
# Right = actual column name in your SQL table       (change these)
COLUMNS = {
    "provider":   "leg.provider",       # LP / liquidity provider name
    "symbol":     "order.symbol",       # instrument symbol
    "bid":        "order.bid",          # bid price
    "ask":        "order.ask",          # ask price
    "size":       "deal.size",          # deal size in lots
    "digits":     "order.digits",       # decimal digits for pip calc
    "timestamp":  "order.open_milli",   # Unix timestamp in milliseconds
    # ── Optional columns (set value to None to disable) ──────────────────────
    "leg_provider": "leg.provider",     # duplicate of provider (kept for PrimeXM)
    "markup":     "deal.markup",        # client markup (optional)
    "fill_price": "order.fillprice",    # fill price (optional)
}

# ── Default filter values ─────────────────────────────────────────────────────
DEFAULT_TOP_N_PROVIDERS = 20    # max providers shown in bar chart
DEFAULT_HEATMAP_METRIC   = "weighted_avg_spread"

# ── Cache TTL (seconds) ───────────────────────────────────────────────────────
CACHE_TTL = 300     # 5 minutes; Streamlit re-fetches data after this
