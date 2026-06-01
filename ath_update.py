import json
import pandas as pd
import gspread
from tvDatafeed import TvDatafeed, Interval
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------------
# Load credentials from GitHub Secret
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

sheet = client.open("ATH_NSE").worksheet("ATH_TV")

sheet.update(
    "A1:F1",
    [[
        "Symbol",
        "Prev_Close",
        "Monthly20SMA",
        "ATH",
        "ATH_Date",
        "ATH_%"
    ]]
)

symbols = sheet.col_values(1)[1:]

tv = TvDatafeed()

results = []

for symbol in symbols:

    try:

        print(f"Processing {symbol}")

        df = tv.get_hist(
            symbol=symbol.strip(),
            exchange="NSE",
            interval=Interval.in_monthly,
            n_bars=300
        )

        if df is None or len(df) < 25:
            raise Exception("No Data")

        # Ignore current incomplete month
        df = df.iloc[:-1]

        prev_close = round(df["close"].iloc[-1], 2)

        sma20 = round(
            df["close"].rolling(20).mean().iloc[-1],
            2
        )

        ath = round(df["high"].max(), 2)

        ath_date = (
            df[df["high"] == ath]
            .index[-1]
            .strftime("%Y-%m")
        )

        ath_pct = round(
            ((prev_close - ath) / ath) * 100,
            2
        )

        results.append([
            prev_close,
            sma20,
            ath,
            ath_date,
            ath_pct
        ])

    except Exception as e:

        print(symbol, e)

        results.append([
            "",
            "",
            "",
            "",
            ""
        ])

sheet.update(
    f"B2:F{len(results)+1}",
    results
)

print("Update Completed")
