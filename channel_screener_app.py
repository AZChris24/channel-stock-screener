import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import time

st.set_page_config(page_title="Channel Stock Screener", layout="wide")
st.title("📈 Channel Stock Screener (Under $20)")

# Suppress yfinance warnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

@st.cache_data
def load_all_us_tickers():
    url = "https://raw.githubusercontent.com/datasets-us/stock-tickers/master/data/all_tickers.csv"
    df = pd.read_csv(url)
    tickers = df['ticker'].dropna().unique().tolist()
    return tickers

# Helper function to check if a stock is trading in a channel
def is_channel_stock(df, tolerance=0.03, min_bounces=4):
    if df is None or df.empty or len(df) < 20:
        return False, None, None

    highs = df['High']
    lows = df['Low']

    support = float(lows.min())
    resistance = float(highs.max())
    range_width = resistance - support

    if support == 0 or pd.isna(support) or pd.isna(resistance):
        return False, None, None

    bounces = 0
    for close in df['Close']:
        if ((close < (support + tolerance * range_width)) or
            (close > (resistance - tolerance * range_width))):
            bounces += 1

    is_bounce_enough = bounces >= min_bounces
    is_narrow_range = (range_width / support) < 0.2

    return is_bounce_enough and is_narrow_range, support, resistance

# Streamlit interface
max_price = st.slider("Maximum stock price:", 1, 50, 20)
all_tickers = load_all_us_tickers()
selected = st.multiselect("Optionally scan only a few tickers:", all_tickers[:1000], [])

scan_list = selected if selected else all_tickers

progress = st.progress(0)
detected = []

for i, ticker in enumerate(scan_list):
    progress.progress(i / len(scan_list))
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty:
            continue
        last_close = df['Close'].iloc[-1]
        if last_close > max_price:
            continue

        result, support, resistance = is_channel_stock(df)
        if result:
            detected.append({
                'Ticker': ticker,
                'Price': round(last_close, 2),
                'Support': round(support, 2),
                'Resistance': round(resistance, 2)
            })
        time.sleep(0.1)  # Be gentle with Yahoo
    except Exception as e:
        continue

st.success("Scan complete.")

if detected:
    st.subheader("Detected Channel Stocks")
    st.dataframe(pd.DataFrame(detected))
else:
    st.info("No channel stocks under $20 detected at the moment.")
