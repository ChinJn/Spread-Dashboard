# LP Spread Monitor Dashboard

A Streamlit web dashboard for monitoring liquidity provider (LP) spread data from a PrimeXM MySQL database.

---

## What This Dashboard Shows

- **KPI Cards** — Overall weighted avg spread, min, max, avg spread, total volume, trade count
- **Provider Ranking** — Bar chart ranking LPs by weighted average spread
- **Spread Over Time** — Line chart resampled by time bucket (15 min / 1 hour / 4 hours / 1 day)
- **Provider × Hour Heatmap** — Spread intensity by provider and hour of day
- **Hourly Spread Table** — Per hour, per symbol, per provider breakdown with all spread metrics
- **Detailed Stats Table** — Provider × symbol aggregation with CSV export
- **Raw Data Preview** — First 500 rows of filtered data with CSV export

---

## Requirements

- Python 3.10 or higher
- Internet access to install packages
- Your public IP must be **whitelisted** on the PrimeXM database server (port 3306)

---

## Setup Instructions (First Time)

### Step 1 — Download the code

Clone or download this repository to your laptop:

```
git clone <repository-url>
cd Spread-Dashboard
```

Or download the ZIP from GitHub and extract it.

---

### Step 2 — Install Python

Download and install Python from [https://www.python.org/downloads](https://www.python.org/downloads)

> **IMPORTANT:** During installation, tick the checkbox **"Add Python to PATH"** before clicking Install.

Verify Python is installed by opening a terminal and running:

```
python --version
```

---

### Step 3 — Create a virtual environment

Open a terminal (PowerShell or Command Prompt) inside the project folder and run:

```
python -m venv spread
```

Activate the virtual environment:

```
spread\Scripts\activate
```

You should see `(spread)` appear at the start of your terminal prompt.

---

### Step 4 — Install dependencies

With the virtual environment activated, run:

```
pip install -r requirements.txt
```

---

### Step 5 — Set up your credentials

Create a file named `.env` in the project folder (same folder as `dashboard_py.py`).

Copy and paste the following into the `.env` file and fill in the values:

```
PXM_SERVER = 'pxm.tradesdbpro01.rep.ext.primexm.com'
PXM_PORT   = '3306'
PXM_UID    = 'your_username'
PXM_PWD    = 'your_password'
PXM_DB     = 'live_finpoints_xcore_uk_trade'
```

> **Note:** The `.env` file contains sensitive credentials. Never share this file or commit it to GitHub.

---

### Step 6 — Whitelist your IP address

The PrimeXM server only allows connections from approved IP addresses.

1. Find your public IP by running this in the terminal:
   ```
   curl ifconfig.me
   ```
2. Send your IP address to the database administrator and request it to be **whitelisted on port 3306**.
3. Once approved, you can connect to the live database.

> While waiting for approval, you can still use the dashboard with **sample data** by toggling "Use sample data" in the sidebar.

---

### Step 7 — Run the dashboard

With the virtual environment activated, run:

```
streamlit run dashboard_py.py
```

The dashboard will open automatically in your browser at `http://localhost:8501`

---

## How to Use the Dashboard

### Sidebar Controls

| Control | Description |
|---|---|
| **Use sample data** | Toggle ON to run without a database connection (uses generated demo data) |
| **Date range (From / To)** | Select the date range to query from the database |
| **Time bucket** | Controls how the Spread Over Time chart is resampled (15 min, 1 hour, 4 hours, 1 day) |
| **Top N providers** | How many providers to show in the bar chart ranking |
| **Symbol filter** | Filter charts and tables to specific trading symbols |
| **Provider filter** | Filter charts and tables to specific LP providers |

### Typical Workflow

1. Turn off **"Use sample data"** to connect to the live database
2. Set your **date range** (avoid large ranges like a full month — it queries 145GB+ tables)
3. Use the **Symbol** and **Provider** filters to narrow down your view
4. Check the **Hourly Spread Table** to see spread breakdown by hour
5. Export data using the **CSV download buttons** at the bottom

---

## Running the Dashboard Again (After First Setup)

Every time you want to run the dashboard after the initial setup:

1. Open a terminal in the project folder
2. Activate the virtual environment:
   ```
   spread\Scripts\activate
   ```
3. Run the dashboard:
   ```
   streamlit run dashboard_py.py
   ```

---

## Project File Structure

```
Spread-Dashboard/
│
├── dashboard_py.py     # Main Streamlit app — UI, charts, tables
├── db.py               # Database connection and SQL queries
├── transform.py        # Data cleaning and all aggregation calculations
├── config.py           # Settings: timezone, cache TTL, display defaults
├── requirements.txt    # Python package dependencies
├── .env                # Your database credentials (NOT shared/committed)
└── README.md           # This file
```

---

## Troubleshooting

### "python is not recognized"
Python is not installed or not added to PATH. Reinstall Python and tick **"Add Python to PATH"**.

### "Can't connect to MySQL server (timed out)"
Your IP address is not whitelisted. Run `curl ifconfig.me` and send the result to the database administrator.

### "No module named streamlit" or similar
The virtual environment is not activated. Run `spread\Scripts\activate` first.

### Dashboard is slow or times out on large date ranges
The `deal` table is 145GB and `order` is 266GB. Keep date ranges short (1–7 days). The dashboard caches results for 5 minutes so re-runs within the same session are fast.

### Data looks wrong or spread values seem too large
Check that you are filtering to a **single symbol** — mixing symbols with different price scales (e.g. EURUSD vs XAUUSD) makes the spread averages misleading.

---

## Notes for Administrators

- The database credentials in `.env` must be kept confidential
- Each colleague's public IP must be individually whitelisted on the PrimeXM server
- The `spreadvenv/` or `spread/` folder (virtual environment) should **not** be committed to GitHub — it is machine-specific
- The `.env` file should **not** be committed to GitHub — add it to `.gitignore`
