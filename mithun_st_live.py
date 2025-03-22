import credentials as crs
import pandas as pd
import numpy as np
import time
from fyers_apiv3 import fyersModel
import datetime

# Load Fyers API Access Token
with open("access.txt", "r") as f:
    access_token = f.read().strip()

client_id = crs.client_id
fyers = fyersModel.FyersModel(client_id=client_id, token=access_token, log_path="")

# Live Market Parameters
CAPITAL_PER_TRADE = 50000  # Amount allocated per trade
RISK_PERCENTAGE = 1  # Risk % per trade

# Function to fetch live 15-minute data
def fetch_live_data(symbol):
    data = {
        "symbol": f"NSE:{symbol}-EQ",
        "resolution": "15",
        "date_format": "1",
        "range_from": (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d'),
        "range_to": datetime.datetime.now().strftime('%Y-%m-%d'),
        "cont_flag": "1"
    }

    response = fyers.history(data)
    if response["s"] == "error":
        print(f"Error fetching data for {symbol}: {response['message']}")
        return None

    df = pd.DataFrame(response["candles"], columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s") + pd.Timedelta(hours=5, minutes=30)
    df.set_index("timestamp", inplace=True)
    return df

# Function to calculate ATR
def calculate_atr(df, period=14):
    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(abs(df["high"] - df["close"].shift(1)), abs(df["low"] - df["close"].shift(1)))
    )
    df["atr"] = df["tr"].rolling(period).mean()
    df.drop(columns=["tr"], inplace=True)
    return df

# Function to compute Supertrend
def supertrend(df, period, multiplier):
    df = calculate_atr(df, period)
    df["basic_upper_band"] = (df["high"] + df["low"]) / 2 + (multiplier * df["atr"])
    df["basic_lower_band"] = (df["high"] + df["low"]) / 2 - (multiplier * df["atr"])
    df["supertrend"] = np.nan
    df["trend"] = np.nan

    df.loc[df.index[0], "supertrend"] = df.loc[df.index[0], "basic_upper_band"]
    df.loc[df.index[0], "trend"] = -1

    for i in range(1, len(df)):
        prev_close = df["close"].iloc[i-1]
        prev_supertrend = df["supertrend"].iloc[i-1]
        upper_band = df["basic_upper_band"].iloc[i]
        lower_band = df["basic_lower_band"].iloc[i]

        if prev_close > prev_supertrend:
            df.loc[df.index[i], "supertrend"] = max(lower_band, prev_supertrend)
            df.loc[df.index[i], "trend"] = 1
        else:
            df.loc[df.index[i], "supertrend"] = min(upper_band, prev_supertrend)
            df.loc[df.index[i], "trend"] = -1

    df["supertrend_signal"] = df["trend"] == 1
    return df

# Function to place order
def place_order(symbol, qty, side):
    order = {
        "symbol": f"NSE:{symbol}-EQ",
        "qty": int(qty),
        "type": 2,  # Market Order
        "side": 1 if side == "BUY" else -1,
        "productType": "INTRADAY",
        "limitPrice": 0,
        "stopPrice": 0,
        "validity": "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
    }
    response = fyers.place_order(order)
    print(f"Order Response for {symbol}: {response}")
    return response

	
# Live Trading Logic
def live_trading(symbol):
    df = fetch_live_data(symbol)
    if df is None:
        return

    df = supertrend(df, period=4, multiplier=2)
    df["supertrend_4_2"] = df["supertrend_signal"]
    df["supertrend_4_2_value"] = df["supertrend"]
    df = supertrend(df, period=5, multiplier=3)
    df["supertrend_5_3"] = df["supertrend_signal"]
    df["supertrend_5_3_value"] = df["supertrend"]

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    atr = latest["atr"]

    qty = int(CAPITAL_PER_TRADE / latest["close"])
    stop_loss = latest["supertrend_4_2_value"] - (0.5 * atr)
    target = latest["close"] + (2 * atr)

    if (prev["close"] > prev["supertrend_4_2_value"] and prev["close"] > prev["supertrend_5_3_value"]):
        print(f"BUY Signal on {symbol} at {latest.name}")
        place_order(symbol, qty, "BUY")

    elif (prev["close"] < prev["supertrend_4_2_value"] and prev["close"] < prev["supertrend_5_3_value"]):
        print(f"SELL Signal on {symbol} at {latest.name}")
        place_order(symbol, qty, "SELL")

    print(f"Stop Loss: {stop_loss:.2f}, Target: {target:.2f}")

# Read stock list and start live trading
with open("stock_list.txt", "r") as file:
    stocks = [line.strip() for line in file.readlines()]

while True:
    print("Fetching live data...")
    for stock in stocks:
        live_trading(stock)
    print("Waiting for next interval...")
    time.sleep(900)  # Wait for next 15-minute candle
