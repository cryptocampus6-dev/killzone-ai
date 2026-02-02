import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime

# --- SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWIMq--iOTVBE4BA"

# Page Config
st.set_page_config(page_title="Ghost Protocol Dashboard", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- FUNCTIONS ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else:
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
        return True
    except: return False

def get_data(symbol):
    try:
        exchange = ccxt.mexc({'options': {'defaultType': 'swap'}})
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except: return pd.DataFrame()

def analyze(df):
    if df.empty: return "NEUTRAL", 50, 0, 0
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    curr = df.iloc[-1]
    
    score = 50
    if curr['close'] > curr['sma50']: score += 15
    else: score -= 15
    if curr['rsi'] < 30: score += 20
    elif curr['rsi'] > 70: score -= 20
    
    sig = "LONG" if score >= 75 else "SHORT" if score <= 25 else "NEUTRAL"
    return sig, score, curr['close'], curr['atr']

# --- SESSION STATE INITIALIZATION ---
if 'coins' not in st.session_state:
    st.session_state.coins = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "PEPE"]
if 'history' not in st.session_state:
    st.session_state.history = []
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False

# --- SIDEBAR UI ---
st.sidebar.title("🎛️ Control Panel")

# System Status
status_color = "green" if st.session_state.bot_active else "red"
status_text = "RUNNING 🟢" if st.session_state.bot_active else "STOPPED 🔴"
st.sidebar.markdown(f"### Status: **:{status_color}[{status_text}]**")

# Start/Stop Buttons
col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START ENGINE"):
    st.session_state.bot_active = True
    st.rerun()
if col2.button("⏹️ STOP ENGINE"):
    st.session_state.bot_active = False
    st.rerun()

st.sidebar.markdown("---")

# Coin Manager
st.sidebar.subheader("🪙 Coin Manager")
new_coin = st.sidebar.text_input("Add Coin (e.g. ADA)", "").upper()
if st.sidebar.button("➕ Add Coin"):
    if new_coin and new_coin not in st.session_state.coins:
        st.session_state.coins.append(new_coin)
        st.success(f"{new_coin} Added!")
    elif new_coin in st.session_state.coins:
        st.sidebar.warning("Coin already exists!")

remove_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove Selected"):
    if remove_coin in st.session_state.coins:
        st.session_state.coins.remove(remove_coin)
        st.rerun()

st.sidebar.markdown("---")
# Test Button
if st.sidebar.button("📡 Test Telegram"):
    send_telegram("🔔 <b>Manual Test:</b> Dashboard is connected!")
    st.sidebar.success("Sent!")

# --- MAIN DASHBOARD ---
st.title("👻 GHOST PROTOCOL : DASHBOARD")

# Live Clock
now_live = datetime.now(lz).strftime("%H:%M:%S")
st.metric("🇱🇰 Sri Lanka Time", now_live)

# Dashboard Layout
tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

with tab1:
    if st.session_state.bot_active:
        st.success("✅ Engine is Running... Scanning Market every 15 mins.")
        
        # This loop runs continuously when active
        placeholder = st.empty()
        
        # Run Loop Logic
        # Note: In Streamlit Cloud, we iterate a few times and then sleep to prevent timeout, 
        # or rely on UptimeRobot to keep triggering it.
        # Here we use a loop that updates the UI.
        
        coins_list = st.session_state.coins
        placeholder.markdown(f"**🔍 Scanning {len(coins_list)} Coins: {', '.join(coins_list)}**")
        
        current_time = datetime.now(lz)
        
        # Only scan if minutes are 00, 15, 30, 45 (approx) to save resources
        # Or just scan every loop for demo
        # For real usage:
        if current_time.minute % 15 == 0 and current_time.second < 40:
            progress_bar = st.progress(0)
            for i, coin in enumerate(coins_list):
                try:
                    df = get_data(f"{coin}/USDT:USDT")
                    if not df.empty:
                        sig, score, price, atr = analyze(df)
                        
                        if sig != "NEUTRAL":
                            # Send Alert
                            send_telegram("", is_sticker=True)
                            sl_dist = atr * 1.5
                            tp_dist = sl_dist
                            if sig == "LONG":
                                sl = price - sl_dist
                                tps = [price + tp_dist*x for x in range(1, 5)]
                            else:
                                sl = price + sl_dist
                                tps = [price - tp_dist*x for x in range(1, 5)]
                            
                            rr = round(abs(tps[3]-price)/abs(price-sl), 2)
                            msg = (f"💎 <b>VIP SIGNAL</b>\n\n"
                                   f"🪙 <b>{coin}/USDT</b>\n"
                                   f"Direction: <b>{sig}</b>\n"
                                   f"Entry: {price:.4f}\n"
                                   f"Targets: {tps[0]:.4f} | {tps[1]:.4f} | {tps[2]:.4f}\n"
                                   f"Stop Loss: {sl:.4f}\n"
                                   f"RR: 1:{rr}")
                            send_telegram(msg)
                            
                            # Log to History
                            log_entry = {
                                "Time": current_time.strftime("%H:%M"),
                                "Coin": coin,
                                "Signal": sig,
                                "Price": price,
                                "Score": score
                            }
                            st.session_state.history.insert(0, log_entry)
                    
                    progress_bar.progress((i + 1) / len(coins_list))
                except: pass
            
            st.success("Scan Complete!")
            time.sleep(60) # Wait to avoid double signals in same minute
            st.rerun()
            
        else:
            time.sleep(1) # Idle wait
            if current_time.second % 10 == 0:
                st.rerun() # Refresh clock
            
    else:
        st.warning("⚠️ Engine is STOPPED. Click 'START ENGINE' in sidebar.")

with tab2:
    st.subheader("Recent Signals")
    if st.session_state.history:
        st.table(pd.DataFrame(st.session_state.history))
    else:
        st.info("No signals generated yet since last reboot.")
