import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
st.set_page_config(page_title="Channel Stock Screener", layout="wide")
st.title("Channel Stock Screener - NASDAQ + NYSE Under $20")

# === 1. Load ticker symbols from GitHub mirrors ===
@st.cache_data(ttl=3600)
def load_all_us_tickers():
    nasdaq_url = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
    nyse_url = "https://raw.githubusercontent.com/datasets/nyse-listed/master/data/nyse-listed.csv"

    nasdaq_df = pd.read_csv(nasdaq_url)
    nyse_df = pd.read_csv(nyse_url)

    nasdaq_symbols = nasdaq_df[nasdaq_df['Test Issue'] == 'N']['Symbol'].tolist()
    nyse_symbols = nyse_df[(nyse_df['Test Issue'] == 'N') & (nyse_df['ETF'] == 'N')]['ACT Symbol'].tolist()

    return sorted(set(nasdaq_symbols + nyse_symbols))

# === 2. Filter tickers for price under $20 ===
@st.cache_data(ttl=600)
def filter_under_20(tickers):
    valid = []
    for ticker in tickers:
        try:
            price = yf.Ticker(ticker).history(period='1d')['Close'][-1]
            if price < 20:
                valid.append(ticker)
        except Exception:
            continue
    return valid

# === 3. Channel pattern detection ===
def is_channel_stock(df, tolerance=0.08, min_bounces=2):
    highs = df['High'].rolling(window=10).max()
    lows = df['Low'].rolling(window=10).min()

    if highs.empty or lows.empty:
        return False, None, None

    support = float(lows.tail(1).iloc[0])
    resistance = float(highs.tail(1).iloc[0])
    range_width = resistance - support

    if support == 0 or np.isnan(support) or np.isnan(resistance):
        return False, None, None

    close = df['Close']
    bounces = ((close > (resistance - tolerance * range_width)) |
               (close < (support + tolerance * range_width))).sum()

    is_channel = (bounces >= min_bounces) and ((range_width / support) < 0.2)
    return is_channel, support, resistance

# === 4. Run Screener ===
with st.spinner("Loading ticker lists..."):
    all_tickers = load_all_us_tickers()
    st.write(f"Loaded {len(all_tickers)} common stock tickers from NASDAQ + NYSE.")

with st.spinner("Filtering stocks under $20..."):
    tickers_under_20 = filter_under_20(all_tickers)
    st.write(f"{len(tickers_under_20)} stocks found under $20.")

matches = []
progress = st.progress(0)

for i, ticker in enumerate(tickers_under_20):
    try:
        df = yf.download(ticker, period='6mo', interval='1d', progress=False)
        if df.empty:
            continue
        result, support, resistance = is_channel_stock(df)
        if result:
            last_price = df['Close'].iloc[-1]
            matches.append({
                "Ticker": ticker,
                "Last Price": f"${last_price:.2f}",
                "Support": f"${support:.2f}",
                "Resistance": f"${resistance:.2f}"
            })
    except Exception:
        continue
    progress.progress((i + 1) / len(tickers_under_20))

# === 5. Show results ===
st.subheader("Detected Channel Stocks Under $20")

if matches:
    df_results = pd.DataFrame(matches)
    st.dataframe(df_results)
    st.download_button("Download CSV", df_results.to_csv(index=False), file_name="channel_stocks_under_20.csv")
else:
    st.info("No channel stocks under $20 detected at the moment.")
