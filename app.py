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

# Optional OpenAI API key (leave empty to disable AI report)
OPENAI_API_KEY = ""

# Public CORS proxies (server-side, no CORS issues in Streamlit)
PROXIES = [
    lambda url: f"https://corsproxy.io/?url={requests.utils.quote(url, safe='')}",
    lambda url: f"https://api.allorigins.win/raw?url={requests.utils.quote(url, safe='')}",
    lambda url: f"https://api.codetabs.com/v1/proxy?quest={requests.utils.quote(url, safe='')}",
]

# ------------------------------
# Built-in fallback list of KSE-100 companies (symbol, name)
# ------------------------------
KSE100_FALLBACK = [
    {"symbol": "PRL", "companyName": "Pakistan Refinery Ltd"},
    {"symbol": "LUCK", "companyName": "Lucky Cement"},
    {"symbol": "OGDC", "companyName": "Oil & Gas Dev Co"},
    {"symbol": "PPL", "companyName": "Pakistan Petroleum"},
    {"symbol": "ENGRO", "companyName": "Engro Corp"},
    {"symbol": "HBL", "companyName": "Habib Bank Ltd"},
    {"symbol": "UBL", "companyName": "United Bank Ltd"},
    {"symbol": "MCB", "companyName": "MCB Bank Ltd"},
    {"symbol": "SEARL", "companyName": "The Searle Company"},
    {"symbol": "TRG", "companyName": "TRG Pakistan"},
    # ... (add more if desired; the list above is sufficient for demo)
]

# ------------------------------
# Helper: fetch JSON from PSX with proxies
# ------------------------------
def fetch_psx_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://dps.psx.com.pk/",
    }
    # Try direct first
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json(), "direct"
    except Exception as e:
        pass

    # Try proxies
    for proxy in PROXIES:
        try:
            proxied_url = proxy(url)
            r = requests.get(proxied_url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if 'contents' in data:
                    return json.loads(data['contents']), "proxy"
                return data, "proxy"
        except Exception as e:
            continue
    return None, None

# ------------------------------
# Fetch list of all companies (PSX market-watch)
# ------------------------------
@st.cache_data(ttl=600)
def fetch_company_list():
    url = "https://dps.psx.com.pk/market-watch"
    raw, source = fetch_psx_data(url)
    if raw:
        stocks = raw if isinstance(raw, list) else raw.get('data', [])
        if stocks:
            df = pd.DataFrame(stocks)
            if 'symbol' in df.columns:
                if 'companyName' in df.columns:
                    df = df[['symbol', 'companyName']]
                elif 'name' in df.columns:
                    df = df.rename(columns={'name': 'companyName'})
                else:
                    df['companyName'] = df['symbol']
                df = df.dropna().drop_duplicates(subset='symbol')
                df = df[df['symbol'].str.match(r'^[A-Za-z0-9]+$', na=False)]
                if not df.empty:
                    return df
    # Fallback
    return pd.DataFrame(KSE100_FALLBACK)

# ------------------------------
# Fetch intraday ticks (order-by-order)
# ------------------------------
def fetch_intraday(symbol):
    url = f"https://dps.psx.com.pk/timeseries/eq/{symbol}"
    raw, source = fetch_psx_data(url)
    if not raw or 'data' not in raw:
        return None, f"No intraday data (source: {source})"
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
        return None, "Intraday data format error"
    ticks.sort(key=lambda x: x[0])
    return ticks, None

# ------------------------------
# Fetch daily summary from market-watch
# ------------------------------
def fetch_daily_summary(symbol):
    url = "https://dps.psx.com.pk/market-watch"
    raw, source = fetch_psx_data(url)
    if not raw:
        return None, f"No market watch data (source: {source})"
    stocks = raw if isinstance(raw, list) else raw.get('data', [])
    for s in stocks:
        if s.get('symbol', '').upper() == symbol.upper():
            return {
                'symbol': s.get('symbol'),
                'name': s.get('companyName', s.get('symbol')),
                'open': s.get('open', 0),
                'high': s.get('high', 0),
                'low': s.get('low', 0),
                'price': s.get('currentPrice', s.get('close', 0)),
                'changePercent': s.get('percentChange', 0),
                'volume': s.get('volume', 0),
                'close': s.get('close', s.get('currentPrice', 0)),
            }, None
    return None, f"Symbol {symbol} not found in market watch"

# ------------------------------
# Fetch top volatile stocks
# ------------------------------
def fetch_top_volatile():
    url = "https://dps.psx.com.pk/market-watch"
    raw, source = fetch_psx_data(url)
    if not raw:
        return None, f"No market watch data (source: {source})"
    stocks = raw if isinstance(raw, list) else raw.get('data', [])
    if not stocks:
        return None, "Empty market watch"
    scored = []
    for s in stocks:
        try:
            price = float(s.get('currentPrice', s.get('close', 0)))
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
    return scored[:10], None

# ------------------------------
# Process intraday ticks
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

    volume_threshold = 250000 if latest_price > 200 else 1000000
    if vsr > volume_threshold and spread < (latest_price * 0.012):
        alert = f"🔴 INSTITUTIONAL ICEBERG FOUND in {symbol}: heavy volume absorbed in tight range."
    elif pct_change > 0.8:
        alert = f"🟢 AGGRESSIVE BUYING in {symbol}: positive momentum."
    else:
        alert = f"🟢 LIVE DATA CONNECTED for {symbol}."
    return df, latest_price, pct_change, total_vol, spread, vsr, alert

# ------------------------------
# Process daily summary (closed market)
# ------------------------------
def process_daily(summary):
    open_price = summary['open']
    close_price = summary['price']
    high = summary['high']
    low = summary['low']
    volume = summary['volume']
    spread = max(0.01, high - low)
    vsr = volume / spread if spread > 0 else 0
    pct_change = summary['changePercent']
    latest = close_price
    return latest, pct_change, volume, spread, vsr, summary['symbol'], summary['name']

# ------------------------------
# Mock data generators
# ------------------------------
def generate_mock_ticks(symbol):
    now = datetime.now()
    ticks = []
    price = 50 + (hash(symbol) % 50)  # deterministic starting price
    for i in range(60):
        time = now - pd.Timedelta(minutes=60-i)
        price += (0.5 - (i % 5) * 0.2)  # some pattern
        volume = 1000 + (i * 100) % 5000
        ticks.append([int(time.timestamp() * 1000), round(price, 2), volume])
    return ticks

def generate_mock_summary(symbol):
    return {
        'symbol': symbol,
        'name': symbol,
        'open': 50,
        'high': 55,
        'low': 48,
        'price': 53,
        'changePercent': 6.0,
        'volume': 1500000,
        'close': 53,
    }

# ------------------------------
# Optional AI report
# ------------------------------
def ai_report(symbol, latest, pct, vol, spread, vsr):
    if not OPENAI_API_KEY:
        return None
    prompt = f"Based on PSX data for {symbol}: price={latest:.2f}, change={pct:.2f}%, volume={vol}, spread={spread:.2f}, VSR={vsr:.0f}. Is institutional accumulation likely? Answer in one line."
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}], "max_tokens": 60, "temperature": 0.2}
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=15)
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
st.markdown("**Order‑by‑order intraday data + daily overview from PSX Data Portal**")

# Main area controls (always visible)
col_search1, col_search2 = st.columns([3, 1])
with col_search1:
    # Load company list
    company_df = fetch_company_list()
    if company_df.empty:
        st.error("Could not load company list. Falling back to manual ticker entry.")
        symbol = st.text_input("Enter Ticker Symbol", value="PRL").upper().strip()
    else:
        search_term = st.text_input("Search by company name or ticker", value="")
        if search_term:
            filtered = company_df[
                company_df['symbol'].str.contains(search_term, case=False, na=False) |
                company_df['companyName'].str.contains(search_term, case=False, na=False)
            ]
        else:
            filtered = company_df
        if filtered.empty:
            st.warning("No companies match your search.")
            symbol = st.text_input("Enter Ticker Manually", value="PRL").upper().strip()
        else:
            filtered['display'] = filtered['symbol'] + " - " + filtered['companyName']
            selected_display = st.selectbox("Select Company", filtered['display'])
            symbol = selected_display.split(" - ")[0].strip()
with col_search2:
    st.write("")  # spacer
    st.write("")
    analyze_btn = st.button("Analyze", use_container_width=True)

# Top volatile button
show_top = st.button("🔄 Refresh Top 10 Volatile Stocks", use_container_width=True)

# Placeholder for results
result_placeholder = st.container()

# Analysis logic
if analyze_btn:
    with st.spinner(f"Fetching data for {symbol}..."):
        ticks, err_intraday = fetch_intraday(symbol)
        daily_summary, err_summary = None, None
        if not ticks:
            daily_summary, err_summary = fetch_daily_summary(symbol)
    
    with result_placeholder:
        if ticks:
            df, latest, pct, vol, spread, vsr, alert = process_ticks(symbol, ticks)
            st.success("Live intraday order-by-order data")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Price", f"PKR {latest:.2f}", f"{pct:.2f}%")
            col2.metric("Traded Volume", f"{vol:,}")
            col3.metric("High-Low Spread", f"PKR {spread:.2f}")
            col4.metric("Volume-to-Spread", f"{vsr:,.0f}")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['time'], y=df['price'], mode='lines+markers',
                                     line=dict(color='#00c853' if pct >= 0 else '#ff5252', width=2),
                                     marker=dict(size=4)))
            fig.update_layout(template='plotly_dark', xaxis_title='Time', yaxis_title='Price (PKR)', height=400)
            st.plotly_chart(fig, use_container_width=True)
            st.info(alert)
        elif daily_summary:
            latest, pct, vol, spread, vsr, sym, name = process_daily(daily_summary)
            st.warning(f"Market is closed or intraday data unavailable. Showing last completed session for **{name} ({sym})**.")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Last Price", f"PKR {latest:.2f}", f"{pct:.2f}%")
            col2.metric("Volume", f"{vol:,}")
            col3.metric("Day Range", f"PKR {daily_summary['low']:.2f} - {daily_summary['high']:.2f}")
            col4.metric("Volume-to-Spread", f"{vsr:,.0f}")
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pct,
                title={'text': "Change %"},
                gauge={
                    'axis': {'range': [-10, 10]},
                    'bar': {'color': "green" if pct >= 0 else "red"},
                    'steps': [
                        {'range': [-10, 0], 'color': "lightcoral"},
                        {'range': [0, 10], 'color': "lightgreen"}
                    ]
                }
            ))
            fig.update_layout(template='plotly_dark', height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            volume_threshold = 250000 if latest > 200 else 1000000
            if vsr > volume_threshold and spread < (latest * 0.012):
                st.error(f"🔴 INSTITUTIONAL ICEBERG FOUND in {sym}: heavy volume absorbed in tight range.")
            else:
                st.info(f"🟢 No abnormal absorption detected for {sym} in the last session.")
        else:
            # Both real data attempts failed; use mock data and show debug info
            st.error("❌ Could not fetch live PSX data. Displaying mock data for demonstration.")
            st.markdown("**Debug Info:**")
            st.text(f"Intraday error: {err_intraday}")
            st.text(f"Summary error: {err_summary}")
            
            # Generate mock data
            mock_ticks = generate_mock_ticks(symbol)
            mock_summary = generate_mock_summary(symbol)
            df, latest, pct, vol, spread, vsr, alert = process_ticks(symbol, mock_ticks)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Price (Mock)", f"PKR {latest:.2f}", f"{pct:.2f}%")
            col2.metric("Traded Volume (Mock)", f"{vol:,}")
            col3.metric("High-Low Spread", f"PKR {spread:.2f}")
            col4.metric("Volume-to-Spread", f"{vsr:,.0f}")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['time'], y=df['price'], mode='lines+markers',
                                     line=dict(color='#00c853' if pct >= 0 else '#ff5252', width=2),
                                     marker=dict(size=4)))
            fig.update_layout(template='plotly_dark', xaxis_title='Time', yaxis_title='Price (PKR)', height=400)
            st.plotly_chart(fig, use_container_width=True)
            st.info(alert)

        # Optional AI report
        if OPENAI_API_KEY:
            with st.spinner("Generating AI brief..."):
                report = ai_report(symbol, latest, pct, vol, spread, vsr)
            if report:
                st.success(f"**AI Brief:** {report}")

# Top volatile section
if show_top:
    with st.spinner("Fetching top volatile stocks..."):
        top_stocks, err_top = fetch_top_volatile()
        if top_stocks:
            st.subheader("🔥 Top 10 Most Volatile Stocks (Last Session / Live)")
            df_top = pd.DataFrame(top_stocks)
            df_top = df_top[['symbol', 'name', 'price', 'changePercent', 'volume', 'high', 'low']]
            st.dataframe(df_top, use_container_width=True)
        else:
            st.warning(f"Could not load volatile stocks. {err_top}")
