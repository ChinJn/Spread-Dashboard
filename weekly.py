import mysql.connector
import pandas as pd

# ── Connection ────────────────────────────────────────────────────────────────
conn = mysql.connector.connect(
    host     = "live_finpoints_xcore_uk_clients",
    port     = 3306,
    user     = "live_finpoints_xcore_uk_clients",
    password = "87aIdJk30lLeTxZ9",
    database = "live_finpoints_xcore_uk_trade"
)


# ── Query ─────────────────────────────────────────────────────────────────────
sql = """
WITH order_spreads AS (
    SELECT
        DATE_SUB(DATE(FROM_UNIXTIME(o.open_milli / 1000)),
            INTERVAL WEEKDAY(FROM_UNIXTIME(o.open_milli / 1000)) DAY) AS week_start,
        l.provider                              AS lp,
        o.symbol,
        o.digits,
        o.ask - o.bid                           AS spread_decimal,
        (o.ask - o.bid) * POW(10, o.digits)     AS spread_pips
    FROM `order` o
    JOIN leg l ON l.order = o.order
    WHERE
        o.ask      > 0
        AND o.bid  > 0
        AND l.provider IS NOT NULL
        AND l.batch = 0
),

weekly_agg AS (
    SELECT
        week_start,
        lp,
        symbol,
        AVG(spread_decimal)  AS avg_spread,
        MIN(spread_decimal)  AS min_spread,
        MAX(spread_decimal)  AS max_spread,
        AVG(spread_pips)     AS avg_spread_pips,
        MIN(spread_pips)     AS min_spread_pips,
        MAX(spread_pips)     AS max_spread_pips,
        COUNT(*)             AS order_count
    FROM order_spreads
    GROUP BY
        week_start,
        lp,
        symbol
)

SELECT
    DATE_FORMAT(week_start, '%Y-%m-%d')  AS week_start,
    lp,
    symbol,
    ROUND(avg_spread, 5)                 AS avg_spread,
    ROUND(min_spread, 5)                 AS min_spread,
    ROUND(max_spread, 5)                 AS max_spread,
    ROUND(avg_spread_pips, 2)            AS avg_spread_pips,
    ROUND(min_spread_pips, 2)            AS min_spread_pips,
    ROUND(max_spread_pips, 2)            AS max_spread_pips,
    order_count
FROM weekly_agg
ORDER BY
    week_start DESC,
    lp,
    symbol;
"""

# ── Run & output ──────────────────────────────────────────────────────────────
try:
    df = pd.read_sql(sql, conn)

    # Print to console
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))

    # Also export to CSV
    output_path = "weekly_lp_symbol_spread.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}  ({len(df)} rows)")

finally:
    conn.close()