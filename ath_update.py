import json
import gspread
from tvDatafeed import TvDatafeed, Interval
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------------
# Google Authentication
# ----------------------------------

with open("credentials.json", "r") as f:
    creds_json = json.load(f)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_json,
    scope
)

client = gspread.authorize(creds)

# ----------------------------------
# Open Sheet
# ----------------------------------

sheet = client.open("ATH_NSE").worksheet("ATh_TV")

# Optional: Write headers
sheet.update(
    "A1:G1",
    [[
        "Symbol",
        "Prev_Close",
        "Monthly20SMA",
        "ATH",
        "ATH_Date",
        "ATH_%",
        "Stock_Age"
    ]]
)

# ----------------------------------
# Read Symbols
# ----------------------------------

symbols = [
    s.strip()
    for s in sheet.col_values(1)[1:]
    if s.strip()
]

# ----------------------------------
# TradingView Connection
# ----------------------------------

tv = TvDatafeed()

results = []

# ----------------------------------
# Process Stocks
# ----------------------------------

for symbol in symbols:

    try:

        print(f"Processing {symbol}")

        df = tv.get_hist(
            symbol=symbol,
            exchange="NSE",
            interval=Interval.in_monthly,
            n_bars=300
        )

        if df is None:
            raise Exception("No Data")

        # Remove current incomplete month
        df = df.iloc[:-1]

        months_history = len(df)

        if months_history < 20:
            raise Exception(
                f"Only {months_history} monthly candles"
            )

        prev_close = round(
            df["close"].iloc[-1],
            2
        )

        sma20 = round(
            df["close"].rolling(20).mean().iloc[-1],
            2
        )

        # Safe ATH calculation
        ath_idx = df["high"].idxmax()

        ath = round(
            df.loc[ath_idx, "high"],
            2
        )

        ath_date = ath_idx.strftime("%Y-%m")

        ath_pct = round(
            ((prev_close - ath) / ath) * 100,
            2
        )

        is_50_month_old = (
            "YES"
            if months_history >= 50
            else "NO"
        )

        results.append([
            prev_close,
            sma20,
            ath,
            ath_date,
            ath_pct,
            months_history
        ])

    except Exception as e:

        print(
            f"ERROR | {symbol} | {str(e)}"
        )

        results.append([
            "",
            "",
            "",
            "",
            "",
            "",
        ])

# ----------------------------------
# Write Results
# ----------------------------------

sheet.update(
    f"B2:G{len(results)+1}",
    results
)

print("Update Completed")
