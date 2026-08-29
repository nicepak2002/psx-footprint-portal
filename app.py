import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime
import math

# ------------------------------
# Configuration
# ------------------------------
st.set_page_config(page_title="PSX Institutional Footprint", layout="wide")

# Add your OpenAI API key here if you want AI-generated reports (optional)
OPENAI_API_KEY = ""  # e.g., "sk-..."

# Public CORS proxies (server-side, no CORS issues in Streamlit)
PROXIES = [
    lambda url: f"https://corsproxy.io/?url={requests.utils.quote(url, safe='')}",
    lambda url: f"https://api.allorigins.win/raw?url={requests.utils.quote(url, safe='')}",
    lambda url: f"https://api.codetabs.com/v1/proxy?quest={requests.utils.quote(url, safe='')}",
]

# ------------------------------
# Helper: fetch with proxies
# ------------------------------
def fetch_psx_data(url):
    """Try to fetch JSON from PSX through proxies."""
    headers = {"User-Agent": "Mozilla/5.0"}
    # Try direct first (may work if your IP is allowed)
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass

    # Try proxies
    for proxy in PROXIES:
        try:
            proxied_url = proxy(url)
            r = requests.get(proxied_url, headers=headers, timeout=15)
            if r.status_code == 200:
                # Some proxies wrap JSON in a 'contents' field
                data = r.json()
                if 'contents' in data:
                    return json.loads(data['contents'])
                return data
        except:
            continue
    return None

# ------------------------------
# Fetch intraday ticks for a symbol
# ------------------------------
def fetch_intraday(symbol):
    url = f"https://dps.psx.com.pk/timeseries/eq/{symbol}"
    raw = fetch_psx_data(url)
    if not raw or 'data' not in raw:
        return None
    ticks = []
    for item in raw['data']:
        try:
            ts = datetime.strptime(item['DateTime'], "%Y-%m-%dT%H:%M:%S")
            ts_ms = int(ts.timestamp() * 1000)
            price = float(item['Price'])
            volume = int(item['Volume'])
            ticks.append([ts_ms, price, volume])
        except:
            continue
    if not ticks:
        return None
    # Sort by time
    ticks.sort(key=lambda x: x[0])
    return ticks

# ------------------------------
# Fetch top volatile stocks
# ------------------------------
def fetch_top_volatile():
    url = "https://dps.psx.com.pk/market-watch"
    raw = fetch_psx_data(url)
    if not raw:
        return None
    # The market-watch endpoint may return JSON or HTML; assume JSON array
    stocks = raw if isinstance(raw, list) else raw.get('data', [])
    if not stocks:
        return None
    scored = []
    for s in stocks:
        try:
            price = float(s.get('currentPrice', 0))
            high = float(s.get('high', 0))
            low = float(s.get('low', 0))
            volume = int(s.get('volume', 0))
            if price > 0 and volume > 0 and high >= low:
                score = ((high - low) / price) * math.sqrt(volume / 1000)
                scored.append({
                    'symbol': s.get('symbol', ''),
                    'name': s.get('companyName', s.get('symbol', '')),
                    'price': price,
                    'changePercent': s.get('percentChange', 0),
                    'volume': volume,
                    'high': high,
                    'low': low,
                    'score': score
                })
        except:
            continue
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:10]

# ------------------------------
# Compute metrics and alert
# ------------------------------
def process_ticks(symbol, ticks):
    df = pd.DataFrame(ticks, columns=['timestamp', 'price', 'volume'])
    df['time'] = pd.to_datetime(df['timestamp'], unit='ms')

    latest_price = df['price'].iloc[-1]
    open_price = df['price'].iloc[0]
    high = df['price'].max()
    low = df['price'].min()
    total_vol = df['volume'].sum()
    spread = max(0.01, high - low)
    vsr = total_vol / spread
    pct_change = (latest_price - open_price) / open_price * 100

    # Institutional iceberg heuristic
    volume_threshold = 250000 if latest_price > 200 else 1000000
    if vsr > volume_threshold and spread < (latest_price * 0.012):
        alert = f"🔴 INSTITUTIONAL ICEBERG FOUND in {symbol}: heavy volume absorbed in tight range."
    elif pct_change > 0.8:
        alert = f"🟢 AGGRESSIVE BUYING in {symbol}: positive momentum."
    else:
        alert = f"🟢 LIVE DATA CONNECTED for {symbol}."

    return df, latest_price, pct_change, total_vol, spread, vsr, alert

# ------------------------------
# Optional AI report
# ------------------------------
def ai_report(symbol, latest_price, pct_change, total_vol, spread, vsr):
    if not OPENAI_API_KEY:
        return None
    prompt = (
        f"Based on PSX data for {symbol}: price={latest_price:.2f}, "
        f"change={pct_change:.2f}%, volume={total_vol}, spread={spread:.2f}, "
        f"VSR={vsr:.0f}. Is institutional accumulation likely? Answer in one line."
    )
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
        "temperature": 0.2
    }
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, json=data, timeout=15)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        else:
            return f"AI error: {r.status_code}"
    except Exception as e:
        return f"AI failed: {str(e)}"

# ------------------------------
# Streamlit UI
# ------------------------------
st.title("🛡️ PSX Institutional Footprint")
st.markdown("**Order‑by‑order trade data from PSX Data Portal**")

# Sidebar for symbol input
with st.sidebar:
    st.header("Stock Analysis")
    symbol = st.text_input("Enter Ticker Symbol", value="PRL").upper().strip()
    analyze_btn = st.button("Analyze")
    st.markdown("---")
    st.header("Top 10 Volatile Stocks")
    show_top = st.button("Refresh Top Volatile")
    st.markdown("---")
    st.markdown("Made by Muhammad Usman Saleem")

# Main area
if analyze_btn or symbol:
    with st.spinner(f"Fetching intraday data for {symbol}..."):
        ticks = fetch_intraday(symbol)
    if ticks:
        df, latest, pct, vol, spread, vsr, alert = process_ticks(symbol, ticks)

        # Metrics cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Price", f"PKR {latest:.2f}", f"{pct:.2f}%")
        col2.metric("Traded Volume", f"{vol:,}")
        col3.metric("High-Low Spread", f"PKR {spread:.2f}")
        col4.metric("Volume-to-Spread", f"{vsr:,.0f}")

        st.subheader("Intraday Footprint Chart")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['time'], y=df['price'],
            mode='lines+markers',
            line=dict(color='#00c853' if pct >= 0 else '#ff5252', width=2),
            marker=dict(size=4)
        ))
        fig.update_layout(
            template='plotly_dark',
            xaxis_title='Time',
            yaxis_title='Price (PKR)',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        st.info(alert)

        # Optional AI report
        if OPENAI_API_KEY:
            with st.spinner("Generating AI brief..."):
                report = ai_report(symbol, latest, pct, vol, spread, vsr)
            if report:
                st.success(f"**AI Brief:** {report}")
    else:
        st.error("Failed to fetch PSX data. Market may be closed or symbol invalid.")

# Top volatile section
if show_top:
    with st.spinner("Fetching top volatile stocks..."):
        top_stocks = fetch_top_volatile()
    if top_stocks:
        st.subheader("🔥 Top 10 Most Volatile Stocks (Right Now)")
        df_top = pd.DataFrame(top_stocks)
        df_top = df_top[['symbol', 'name', 'price', 'changePercent', 'volume', 'high', 'low']]
        st.dataframe(df_top, use_container_width=True)
    else:
        st.warning("Could not load volatile stocks. Market may be closed.")
