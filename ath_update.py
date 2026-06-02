import json
import time
import os
import gspread
from concurrent.futures import ThreadPoolExecutor, as_completed
from tvDatafeed import TvDatafeed, Interval
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================================
# GOOGLE AUTH
# ==========================================================

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

# ==========================================================
# READ SYMBOLS
# ==========================================================

symbols = [
    s.strip()
    for s in sheet.col_values(1)[1:]
    if s.strip()
]

print(f"Total Symbols : {len(symbols)}")

# ==========================================================
# TVDATAFEED
# ==========================================================

print("TV_USERNAME exists:", os.getenv("TV_USERNAME") is not None)
print("TV_PASSWORD exists:", os.getenv("TV_PASSWORD") is not None)

tv = TvDatafeed(
    username=os.getenv("TV_USERNAME"),
    password=os.getenv("TV_PASSWORD")
)

# ==========================================================
# PROCESS ONE STOCK
# ==========================================================

def process_stock(symbol):

    try:

        df = None

        for attempt in range(3):

            try:

                df = tv.get_hist(
                    symbol=symbol,
                    exchange="NSE",
                    interval=Interval.in_monthly,
                    n_bars=300
                )

                if df is not None:
                    break

            except Exception:

                time.sleep(3)

        if df is None:
            raise Exception("No Data")

        # remove current month
        df = df.iloc[:-1]

        stock_age = len(df)

        if stock_age < 20:
            raise Exception(
                f"Only {stock_age} monthly candles"
            )

        prev_close = round(
            df["close"].iloc[-1],
            2
        )

        sma20 = round(
            df["close"]
            .rolling(20)
            .mean()
            .iloc[-1],
            2
        )

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

        print(f"OK : {symbol}")

        return (
            symbol,
            [
                prev_close,
                sma20,
                ath,
                ath_date,
                ath_pct,
                stock_age
            ]
        )

    except Exception as e:

        print(
            f"ERROR : {symbol} : {str(e)}"
        )

        return (
            symbol,
            [
                "",
                "",
                "",
                "",
                "",
                ""
            ]
        )

# ==========================================================
# PARALLEL EXECUTION
# ==========================================================

results_dict = {}

MAX_WORKERS = 4

with ThreadPoolExecutor(
    max_workers=MAX_WORKERS
) as executor:

    futures = {
        executor.submit(
            process_stock,
            symbol
        ): symbol
        for symbol in symbols
    }

    completed = 0

    for future in as_completed(futures):

        symbol, result = future.result()

        results_dict[symbol] = result

        completed += 1

        if completed % 50 == 0:

            print(
                f"Completed {completed}/{len(symbols)}"
            )

# ==========================================================
# PRESERVE SHEET ORDER
# ==========================================================

results = [
    results_dict.get(
        symbol,
        ["", "", "", "", "", ""]
    )
    for symbol in symbols
]

# ==========================================================
# WRITE TO GOOGLE SHEET
# ==========================================================

sheet.update(
    f"B2:G{len(results)+1}",
    results
)

print("================================")
print("Update Completed Successfully")
print("================================")
