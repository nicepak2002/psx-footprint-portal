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
# This is used only if the dynamic fetch fails.
# You can expand this list as needed.
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
    {"symbol": "POL", "companyName": "Pakistan Oilfields Ltd"},
    {"symbol": "HUBC", "companyName": "Hub Power Company"},
    {"symbol": "KAPCO", "companyName": "Kot Addu Power Company"},
    {"symbol": "NBP", "companyName": "National Bank of Pakistan"},
    {"symbol": "BAFL", "companyName": "Bank Alfalah Ltd"},
    {"symbol": "FFC", "companyName": "Fauji Fertilizer Company"},
    {"symbol": "EFERT", "companyName": "Engro Fertilizers Ltd"},
    {"symbol": "DGKC", "companyName": "D.G. Khan Cement"},
    {"symbol": "MLCF", "companyName": "Maple Leaf Cement"},
    {"symbol": "FCCL", "companyName": "Fauji Cement Company"},
    {"symbol": "ISL", "companyName": "International Steels Ltd"},
    {"symbol": "ASTL", "companyName": "Amreli Steels Ltd"},
    {"symbol": "SYS", "companyName": "Systems Ltd"},
    {"symbol": "PSO", "companyName": "Pakistan State Oil"},
    {"symbol": "APL", "companyName": "Attock Petroleum Ltd"},
    {"symbol": "SNGP", "companyName": "Sui Northern Gas Pipelines"},
    {"symbol": "SSGC", "companyName": "Sui Southern Gas Company"},
    {"symbol": "PTC", "companyName": "Pakistan Telecommunication Company"},
    {"symbol": "WTL", "companyName": "Worldcall Telecom"},
    {"symbol": "KEL", "companyName": "K-Electric Ltd"},
    {"symbol": "EPCL", "companyName": "Engro Polymer & Chemicals"},
    {"symbol": "LOTCHEM", "companyName": "Lotte Chemical Pakistan"},
    {"symbol": "ATRL", "companyName": "Attock Refinery Ltd"},
    {"symbol": "NRL", "companyName": "National Refinery Ltd"},
    {"symbol": "BYCO", "companyName": "Byco Petroleum Pakistan"},
    {"symbol": "HASCOL", "companyName": "Hascol Petroleum"},
    {"symbol": "PIOC", "companyName": "Pioneer Cement"},
    {"symbol": "CHCC", "companyName": "Cherat Cement"},
    {"symbol": "GWLC", "companyName": "Gharibwal Cement"},
    {"symbol": "JVDC", "companyName": "Javedan Corporation"},
    {"symbol": "ANL", "companyName": "Azgard Nine Ltd"},
    {"symbol": "GATM", "companyName": "Gul Ahmed Textile Mills"},
    {"symbol": "NML", "companyName": "Nishat Mills Ltd"},
    {"symbol": "ILP", "companyName": "Interloop Ltd"},
    {"symbol": "KTML", "companyName": "Kohinoor Textile Mills"},
    {"symbol": "MUGHAL", "companyName": "Mughal Iron & Steel"},
    {"symbol": "ASL", "companyName": "Aisha Steel Mills"},
    {"symbol": "CSAP", "companyName": "Crescent Steel & Allied Products"},
    {"symbol": "INIL", "companyName": "International Industries Ltd"},
    {"symbol": "GHNI", "companyName": "Ghandhara Industries"},
    {"symbol": "GHNL", "companyName": "Ghandhara Nissan"},
    {"symbol": "HCAR", "companyName": "Honda Atlas Cars"},
    {"symbol": "PSMC", "companyName": "Pak Suzuki Motor Company"},
    {"symbol": "INDU", "companyName": "Indus Motor Company"},
    {"symbol": "MTL", "companyName": "Millat Tractors"},
    {"symbol": "AGTL", "companyName": "Al-Ghazi Tractors"},
    {"symbol": "PKGS", "companyName": "Packages Ltd"},
    {"symbol": "SEPL", "companyName": "Security Papers Ltd"},
    {"symbol": "NESTLE", "companyName": "Nestle Pakistan"},
    {"symbol": "COLG", "companyName": "Colgate-Palmolive Pakistan"},
    {"symbol": "UNILEVER", "companyName": "Unilever Pakistan Foods"},
    {"symbol": "GLAXO", "companyName": "GlaxoSmithKline Pakistan"},
    {"symbol": "ABOT", "companyName": "Abbott Laboratories Pakistan"},
    {"symbol": "FEROZ", "companyName": "Ferozsons Laboratories"},
    {"symbol": "AGP", "companyName": "AGP Ltd"},
    {"symbol": "MARI", "companyName": "Mari Petroleum"},
    {"symbol": "PPL", "companyName": "Pakistan Petroleum"},
    {"symbol": "OGDC", "companyName": "Oil & Gas Development Company"},
    {"symbol": "POL", "companyName": "Pakistan Oilfields"},
    {"symbol": "ENGRO", "companyName": "Engro Corporation"},
    {"symbol": "FFBL", "companyName": "Fauji Fertilizer Bin Qasim"},
    {"symbol": "FATIMA", "companyName": "Fatima Fertilizer Company"},
    {"symbol": "AICL", "companyName": "Adamjee Insurance"},
    {"symbol": "EFU", "companyName": "EFU General Insurance"},
    {"symbol": "IGIHL", "companyName": "IGI Holdings"},
    {"symbol": "PAKRI", "companyName": "Pakistan Reinsurance Company"},
    {"symbol": "SHEL", "companyName": "Shell Pakistan"},
    {"symbol": "BOP", "companyName": "Bank of Punjab"},
    {"symbol": "BIPL", "companyName": "Bank Islami Pakistan"},
    {"symbol": "MEBL", "companyName": "Meezan Bank"},
    {"symbol": "BAHL", "companyName": "Bank AL Habib"},
    {"symbol": "AKBL", "companyName": "Askari Bank"},
    {"symbol": "ABL", "companyName": "Allied Bank Ltd"},
    {"symbol": "FABL", "companyName": "Faysal Bank"},
    {"symbol": "HMB", "companyName": "Habib Metropolitan Bank"},
    {"symbol": "JSBL", "companyName": "JS Bank"},
    {"symbol": "SILK", "companyName": "Silkbank"},
    {"symbol": "SNBL", "companyName": "Soneri Bank"},
    {"symbol": "UBL", "companyName": "United Bank"},
    {"symbol": "NBP", "companyName": "National Bank"},
    {"symbol": "MCB", "companyName": "MCB Bank"},
    {"symbol": "HBL", "companyName": "Habib Bank"},
]

# ------------------------------
# Helper: fetch JSON from PSX with proxies
# ------------------------------
def fetch_psx_data(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    for proxy in PROXIES:
        try:
            proxied_url = proxy(url)
            r = requests.get(proxied_url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if 'contents' in data:
                    return json.loads(data['contents'])
                return data
        except:
            continue
    return None

# ------------------------------
# Fetch list of all companies from PSX market-watch
# ------------------------------
@st.cache_data(ttl=600)
def fetch_company_list():
    url = "https://dps.psx.com.pk/market-watch"
    raw = fetch_psx_data(url)
    if raw:
        stocks = raw if isinstance(raw, list) else raw.get('data', [])
        if stocks:
            df = pd.DataFrame(stocks)
            if 'symbol' in df.columns:
                # Use companyName or name column
                if 'companyName' in df.columns:
                    df = df[['symbol', 'companyName']]
                elif 'name' in df.columns:
                    df = df.rename(columns={'name': 'companyName'})
                else:
                    df['companyName'] = df['symbol']
                df = df.dropna().drop_duplicates(subset='symbol')
                df = df[df['symbol'].str.match(r'^[A-Za-z0-9]+$', na=False)]
                return df
    # Fallback to built-in KSE-100 list
    return pd.DataFrame(KSE100_FALLBACK)

# ------------------------------
# Fetch intraday ticks (order-by-order)
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
    ticks.sort(key=lambda x: x[0])
    return ticks

# ------------------------------
# Fetch daily summary from market-watch
# ------------------------------
def fetch_daily_summary(symbol):
    url = "https://dps.psx.com.pk/market-watch"
    raw = fetch_psx_data(url)
    if not raw:
        return None
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
            }
    return None

# ------------------------------
# Fetch top volatile stocks
# ------------------------------
def fetch_top_volatile():
    url = "https://dps.psx.com.pk/market-watch"
    raw = fetch_psx_data(url)
    if not raw:
        return None
    stocks = raw if isinstance(raw, list) else raw.get('data', [])
    if not stocks:
        return None
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
    return scored[:10]

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

with st.sidebar:
    st.header("Stock Analysis")
    
    # Load company list (all PSX listed companies, including KSE-100)
    company_df = fetch_company_list()
    
    if company_df.empty:
        st.error("Could not load company list. Falling back to manual ticker entry.")
        symbol = st.text_input("Enter Ticker Symbol", value="PRL").upper().strip()
    else:
        # Search box for filtering companies
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
            # Create display string for selectbox
            filtered['display'] = filtered['symbol'] + " - " + filtered['companyName']
            selected_display = st.selectbox("Select Company", filtered['display'])
            # Extract symbol from selection
            symbol = selected_display.split(" - ")[0].strip()
    
    analyze_btn = st.button("Analyze")
    st.markdown("---")
    st.header("Top 10 Volatile Stocks")
    show_top = st.button("Refresh Top Volatile")
    st.markdown("---")
    st.markdown("Made by Muhammad Usman Saleem")

# Main analysis area
if analyze_btn or symbol:
    with st.spinner(f"Fetching data for {symbol}..."):
        ticks = fetch_intraday(symbol)
    
    if ticks:
        # Live intraday mode
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
    else:
        with st.spinner("Intraday not available. Fetching last session's summary..."):
            summary = fetch_daily_summary(symbol)
        if summary:
            latest, pct, vol, spread, vsr, sym, name = process_daily(summary)
            st.warning(f"Market is closed or intraday data unavailable. Showing last completed session for **{name} ({sym})**.")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Last Price", f"PKR {latest:.2f}", f"{pct:.2f}%")
            col2.metric("Volume", f"{vol:,}")
            col3.metric("Day Range", f"PKR {summary['low']:.2f} - {summary['high']:.2f}")
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
            st.error("Symbol not found or PSX data unavailable. Please check the ticker or try again later.")

# Optional AI report
if analyze_btn and symbol and OPENAI_API_KEY:
    with st.spinner("Generating AI brief..."):
        report = ai_report(symbol, latest, pct, vol, spread, vsr)
    if report:
        st.success(f"**AI Brief:** {report}")

# Top volatile section
if show_top:
    with st.spinner("Fetching top volatile stocks..."):
        top_stocks = fetch_top_volatile()
    if top_stocks:
        st.subheader("🔥 Top 10 Most Volatile Stocks (Last Session / Live)")
        df_top = pd.DataFrame(top_stocks)
        df_top = df_top[['symbol', 'name', 'price', 'changePercent', 'volume', 'high', 'low']]
        st.dataframe(df_top, use_container_width=True)
    else:
        st.warning("Could not load volatile stocks. Market data unavailable.")
