# dashboard.py
# ─────────────────────────────────────────────────────────────────────────────
# Streamlit entry point.  Run with:   streamlit run dashboard.py
# ─────────────────────────────────────────────────────────────────────────────

import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from db        import fetch_data, fetch_sample_data, fetch_symbols
from transform import (
    clean, add_spread_columns, agg_by_provider,
    agg_by_provider_symbol, spread_over_time,
    heatmap_provider_hour, compute_kpis,
)
from config import CACHE_TTL, DEFAULT_TOP_N_PROVIDERS, DISPLAY_TIMEZONE

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LP Spread Monitor",
    page_icon="📊",
    layout="wide",
)

# ── Colour palette ────────────────────────────────────────────────────────────
ACCENT = "#00B4D8"
GOOD   = "#2DC653"
WARN   = "#F4A261"
BAD    = "#E63946"


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING  (cached so we don't hammer the DB on every widget interaction)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def load(date_from: str, date_to: str, use_sample: bool) -> pd.DataFrame:
    raw = fetch_sample_data() if use_sample else fetch_data(date_from, date_to)
    df  = clean(raw)
    df  = add_spread_columns(df)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR  — global controls (wrapped in a form so nothing runs until Search)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_symbols(use_sample: bool) -> list:
    if use_sample:
        return ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]
    try:
        return fetch_symbols()
    except Exception:
        return []

with st.sidebar:
    st.title("⚙️ Controls")

    use_sample = st.toggle("Use sample data (no DB needed)", value=True)

    with st.form("controls"):
        st.subheader("Date range")
        col_a, col_b = st.columns(2)
        date_from = col_a.date_input("From", value=pd.Timestamp("2024-01-01"))
        date_to   = col_b.date_input("To",   value=pd.Timestamp("2024-01-31"))

        st.subheader("Symbol")
        available_symbols = get_symbols(use_sample)
        sel_symbols = st.multiselect(
            "Select symbols", available_symbols, default=available_symbols[:5] if available_symbols else []
        )

        st.subheader("Resample frequency")
        freq_label = st.selectbox(
            "Time bucket",
            ["15 min", "1 hour", "4 hours", "1 day"],
            index=1,
        )

        st.subheader("Display")
        top_n = st.slider("Top N providers", 3, 30, DEFAULT_TOP_N_PROVIDERS)

        searched = st.form_submit_button("🔍 Search", use_container_width=True)

    tz_label = DISPLAY_TIMEZONE or "UTC"
    st.caption(f"Timezone: **{tz_label}**")

freq_map = {"15 min": "15min", "1 hour": "1h", "4 hours": "4h", "1 day": "1D"}
freq = freq_map[freq_label]

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA  — only runs when Search is clicked
# ─────────────────────────────────────────────────────────────────────────────
if "df_all" not in st.session_state:
    st.info("Set your date range and symbols, then click **🔍 Search**.")
    st.stop()

if searched:
    with st.spinner("Loading data…"):
        st.session_state.df_all = load(str(date_from), str(date_to), use_sample)
    st.session_state.date_from = str(date_from)
    st.session_state.date_to   = str(date_to)

df_all = st.session_state.df_all

if df_all.empty:
    st.error("No data returned. Check your DB connection or date range.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# FILTERS — provider (symbol already chosen before load)
# ─────────────────────────────────────────────────────────────────────────────
all_providers = sorted(df_all["provider"].unique())
sel_providers = st.sidebar.multiselect("Provider", all_providers, default=all_providers)

df = df_all.copy()
if sel_symbols:
    df = df[df["symbol"].isin(sel_symbols)]
if sel_providers:
    df = df[df["provider"].isin(sel_providers)]

if df.empty:
    st.warning("No data matches the current filter selection.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.title("📊 LP Spread Monitor")
st.caption(
    f"Showing **{len(df):,}** rows · "
    f"{df['provider'].nunique()} providers · "
    f"{df['symbol'].nunique()} symbols · "
    f"Period: {date_from} → {date_to}"
)
st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────
kpis = compute_kpis(df)

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("⚖️ Wtd Avg Spread",  f"{kpis['weighted_avg_spread']:.5f}")
k2.metric("📉 Min Spread",       f"{kpis['min_spread']:.5f}")
k3.metric("📈 Max Spread",       f"{kpis['max_spread']:.5f}")
k4.metric("📊 Avg Spread",       f"{kpis['avg_spread']:.5f}")
k5.metric("📦 Total Volume",     f"{kpis['total_volume']:,.1f} lots")
k6.metric("🔢 Trades",           f"{kpis['trade_count']:,}")

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — PROVIDER RANKING BAR CHART
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🏆 Provider Ranking — Weighted Average Spread")

prov_agg = agg_by_provider(df).head(top_n)

fig_bar = px.bar(
    prov_agg,
    x="weighted_avg_spread",
    y="provider",
    orientation="h",
    color="weighted_avg_spread",
    color_continuous_scale=["#2DC653", "#F4A261", "#E63946"],
    text=prov_agg["weighted_avg_spread"].map("{:.5f}".format),
    hover_data={"total_volume": True, "trade_count": True, "avg_spread": True},
    labels={
        "weighted_avg_spread": "Weighted Avg Spread",
        "provider": "LP Provider",
    },
)
fig_bar.update_layout(
    yaxis={"categoryorder": "total ascending"},
    coloraxis_showscale=False,
    margin=dict(l=0, r=0, t=10, b=0),
    height=max(300, top_n * 30),
)
fig_bar.update_traces(textposition="outside")
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — SPREAD OVER TIME (LINE CHART)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📈 Spread Over Time")

ts_df = spread_over_time(df, freq=freq)

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=ts_df["datetime"],
    y=ts_df["weighted_avg_spread"],
    name="Weighted Avg Spread",
    line=dict(color=ACCENT, width=2),
    fill="tozeroy",
    fillcolor="rgba(0,180,216,0.12)",
))
fig_line.add_trace(go.Scatter(
    x=ts_df["datetime"],
    y=ts_df["avg_spread"],
    name="Simple Avg Spread",
    line=dict(color=WARN, width=1.5, dash="dot"),
))
fig_line.update_layout(
    xaxis_title="Time",
    yaxis_title="Spread",
    legend=dict(orientation="h", y=1.05),
    margin=dict(l=0, r=0, t=30, b=0),
    height=350,
)
st.plotly_chart(fig_line, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — HEATMAP: PROVIDER × HOUR
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🌡️ Provider × Hour Heatmap (Weighted Avg Spread)")

pivot = heatmap_provider_hour(df)

# Fill hours with no data as NaN so they render as empty cells
all_hours = list(range(24))
pivot = pivot.reindex(columns=all_hours)

fig_heat = go.Figure(go.Heatmap(
    z=pivot.values,
    x=[f"{h:02d}:00" for h in pivot.columns],
    y=pivot.index.tolist(),
    colorscale="RdYlGn_r",       # red = wide spread (bad), green = tight (good)
    colorbar=dict(title="Spread"),
    hoverongaps=False,
))
fig_heat.update_layout(
    xaxis_title="Hour of Day (local time)",
    yaxis_title="Provider",
    margin=dict(l=0, r=0, t=10, b=0),
    height=max(350, len(pivot) * 28),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — DETAILED TABLE (provider × symbol)
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("📋 Detailed Stats — Provider × Symbol")

detail = agg_by_provider_symbol(df)
detail = detail.sort_values("weighted_avg_spread")

# Format for display
fmt_cols = ["weighted_avg_spread", "min_spread", "max_spread", "avg_spread"]
detail_display = detail.copy()
for c in fmt_cols:
    detail_display[c] = detail_display[c].map("{:.5f}".format)
detail_display["total_volume"] = detail_display["total_volume"].map("{:,.2f}".format)

st.dataframe(
    detail_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "provider":            st.column_config.TextColumn("Provider"),
        "symbol":              st.column_config.TextColumn("Symbol"),
        "weighted_avg_spread": st.column_config.TextColumn("Wtd Avg Spread"),
        "min_spread":          st.column_config.TextColumn("Min Spread"),
        "max_spread":          st.column_config.TextColumn("Max Spread"),
        "avg_spread":          st.column_config.TextColumn("Avg Spread"),
        "total_volume":        st.column_config.TextColumn("Volume (lots)"),
        "trade_count":         st.column_config.NumberColumn("Trades"),
    },
)

# ── CSV export ────────────────────────────────────────────────────────────────
csv_buf = io.StringIO()
detail.to_csv(csv_buf, index=False)
st.download_button(
    label="⬇️ Export table as CSV",
    data=csv_buf.getvalue(),
    file_name="lp_spread_detail.csv",
    mime="text/csv",
)

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — RAW DATA PREVIEW (collapsible)
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("🔍 Raw data preview (first 500 rows)"):
    preview_cols = [
        "datetime", "provider", "symbol",
        "bid", "ask", "spread", "spread_pips", "size",
    ]
    st.dataframe(
        df[preview_cols].head(500),
        use_container_width=True,
        hide_index=True,
    )

    raw_csv = io.StringIO()
    df[preview_cols].to_csv(raw_csv, index=False)
    st.download_button(
        label="⬇️ Export raw data as CSV",
        data=raw_csv.getvalue(),
        file_name="lp_spread_raw.csv",
        mime="text/csv",
    )
