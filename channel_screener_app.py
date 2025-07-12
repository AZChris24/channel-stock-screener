import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import urllib.request

st.set_page_config(page_title="Channel Stock Screener", layout="wide")
st.title("📈 Channel Stock Screener (Near Real-Time)")
st.write("Detects U.S. stocks trading in a sideways channel and under $20.")

@st.cache_data(show_spinner="Loading ticker list...")
def load_all_us_tickers():
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents_symbols.csv"
    df = pd.read_csv(url)
    tickers = df['Symbol'].unique().tolist()
    return tickers

def is_channel_stock(df, tolerance=0.03, min_bounces=4):
    if df is None or df.empty or len(df) < 30:
        return False, None, None

    highs = df["High"].tail(30)
    lows = df["Low"].tail(30)

    support = lows.min()
    resistance = highs.max()

    range_width = resistance - support
    if support == 0 or range_width == 0:
        return False, None, None

    close_prices = df["Close"].tail(30)
    bounces = 0
    for close in close_prices:
        if (abs(close - support) / support < tolerance) or (abs(close - resistance) / resistance < tolerance):
            bounces += 1

    is_bounce_enough = bounces >= min_bounces
    is_narrow_range = (range_width / support) < 0.2

    is_channel = is_bounce_enough and is_narrow_range
    return is_channel, support, resistance

@st.cache_data(show_spinner="Screening tickers...")
def find_channel_stocks(tickers):
    channel_stocks = []

    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            current_price = info.get("currentPrice", None)

            if current_price is None or current_price > 20:
                continue

            df = yf.download(ticker, period="6mo", interval="1d", progress=False)
            result, support, resistance = is_channel_stock(df)

            if result:
                channel_stocks.append({
                    "Ticker": ticker,
                    "Price": current_price,
                    "Support": round(support, 2),
                    "Resistance": round(resistance, 2),
                    "Range %": f"{round((resistance - support) / support * 100, 2)}%"
                })
        except Exception:
            continue

    return pd.DataFrame(channel_stocks)

# Main Execution
all_tickers = load_all_us_tickers()
selected = st.multiselect("🔍 Optional: Filter by specific tickers", options=all_tickers, default=[])

with st.spinner("Scanning for channel stocks under $20..."):
    tickers_to_scan = selected if selected else all_tickers
    results_df = find_channel_stocks(tickers_to_scan)

if not results_df.empty:
    st.success(f"✅ Found {len(results_df)} channel stocks under $20:")
    st.dataframe(results_df, use_container_width=True)
else:
    st.warning("No channel stocks under $20 detected right now.")
