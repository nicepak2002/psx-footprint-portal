import asyncio
import json
import threading
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import websockets

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
BEARER_TOKEN = "YOUR_BEARER_TOKEN"  # Replace with your Capital Stake Token
WEBSOCKET_URL = "wss://csapis.com/2.0/market/feed/l2"

# Global in-memory data store for live ticks
if "market_data" not in st.session_state:
    st.session_state["market_data"] = {}

# -------------------------------------------------------------
# BACKGROUND WEBSOCKET THREAD
# -------------------------------------------------------------
def run_websocket_listener():
    """Asynchronous WebSocket client running in a background thread."""

    async def listen():
        headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
        while True:
            try:
                async with websockets.connect(
                    WEBSOCKET_URL, extra_headers=headers
                ) as ws:
                    print("✅ Connected to Capital Stake Live Feed (Python)")
                    while True:
                        message = await ws.recv()
                        data = json.loads(message)

                        msg_type = data.get("type")
                        payload = data.get("data", {})
                        symbol = payload.get("s")

                        if not symbol:
                            continue

                        symbol = symbol.upper()

                        if symbol not in st.session_state["market_data"]:
                            st.session_state["market_data"][symbol] = {
                                "price": 0.0,
                                "open": 0.0,
                                "high": 0.0,
                                "low": float("inf"),
                                "volume": 0,
                                "ticks": [],
                            }

                        state = st.session_state["market_data"][symbol]

                        # Process Snapshot Tick
                        if msg_type == "tick" and payload.get("c"):
                            state["price"] = float(payload["c"])
                            if not state["open"] and payload.get("o"):
                                state["open"] = float(payload["o"])
                            if payload.get("h"):
                                state["high"] = max(
                                    state["high"], float(payload["h"])
                                )
                            if payload.get("l"):
                                state["low"] = min(
                                    state["low"], float(payload["l"])
                                )
                            if payload.get("v"):
                                state["volume"] = int(payload["v"])

                        # Process Execution / Trade Tick
                        elif msg_type in ["tex", "tor"]:
                            price = float(payload.get("x", 0))
                            vol = int(payload.get("v", 0))

                            if price > 0:
                                state["price"] = price
                                if state["open"] == 0:
                                    state["open"] = price
                                state["high"] = max(state["high"], price)
                                state["low"] = min(state["low"], price)
                                state["volume"] += vol

                                # Append to tick stream history (rolling window of 300)
                                state["ticks"].append(
                                    {
                                        "time": time.strftime("%H:%M:%S"),
                                        "price": price,
                                        "volume": vol,
                                    }
                                )
                                if len(state["ticks"]) > 300:
                                    state["ticks"].pop(0)

            except Exception as e:
                print(f"WS Error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    asyncio.run(listen())


# Start background thread once when Streamlit app initializes
@st.cache_resource
def start_background_feed():
    thread = threading.Thread(target=run_websocket_listener, daemon=True)
    thread.start()


start_background_feed()

# -------------------------------------------------------------
# STREAMLIT UI LAYOUT
# -------------------------------------------------------------
st.set_page_config(
    page_title="PSX Footprint Portal", page_icon="🛡️", layout="wide"
)

st.title("🛡️ PSX Institutional Footprint")
st.caption("Portal Made by Muhammad Usman Saleem | 0316-8232737")

# Search / Ticker Selection
symbol_input = (
    st.text_input("Enter Stock Ticker:", value="PRL").strip().upper()
)

# Placeholder container for real-time dynamic rerendering
placeholder = st.empty()

# Real-time auto-refresh loop (Updates every 1 second)
while True:
    with placeholder.container():
        data = st.session_state["market_data"].get(symbol_input)

        if not data or not data["ticks"]:
            st.info(
                f"Connecting & waiting for live trade execution ticks for **{symbol_input}**..."
            )
        else:
            latest_price = data["price"]
            open_price = data["open"] if data["open"] > 0 else latest_price
            pct_change = (
                ((latest_price - open_price) / open_price) * 100
                if open_price > 0
                else 0.0
            )

            high_p = data["high"]
            low_p = (
                data["low"] if data["low"] != float("inf") else latest_price
            )
            spread = max(0.01, high_p - low_p)
            total_vol = data["volume"]
            vsr = int(total_vol / spread) if spread > 0 else 0

            # Alert Box Engine
            volume_threshold = 250000 if latest_price > 200 else 1000000
            if vsr > volume_threshold and spread < (latest_price * 0.012):
                st.error(
                    f"🔴 **INSTITUTIONAL ICEBERG FOUND ({symbol_input}):** Heavy volume ({total_vol:,} shares) absorbed within PKR {spread:.2f} range."
                )
            else:
                st.success(
                    f"🟢 **LIVE STREAM ACTIVE ({symbol_input}):** Real-time order flow updating."
                )

            # Top Metrics Cards
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(
                "Price",
                f"PKR {latest_price:.2f}",
                delta=f"{pct_change:+.2f}%",
            )
            col2.metric("Traded Volume", f"{total_vol:,}")
            col3.metric("High-Low Spread", f"PKR {spread:.2f}")
            col4.metric("Volume-to-Spread Ratio", f"{vsr:,}")

            # Plotly Chart
            df_ticks = pd.DataFrame(data["ticks"])
            line_color = "#00c853" if pct_change >= 0 else "#ff5252"

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_ticks["time"],
                    y=df_ticks["price"],
                    mode="lines+markers",
                    name="Price",
                    line=dict(color=line_color, width=2),
                )
            )

            fig.update_layout(
                title=f"{symbol_input} Real-Time Tick Stream",
                xaxis_title="Time",
                yaxis_title="Price (PKR)",
                template="plotly_dark",
                height=450,
                margin=dict(l=20, r=20, t=40, b=20),
            )

            st.plotly_chart(fig, use_container_width=True)

    # Sleep 1 second before refreshing UI frame
    time.sleep(1)
