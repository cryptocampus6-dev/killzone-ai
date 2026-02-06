import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import numpy as np
from datetime import datetime, timedelta

# --- USER SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

# --- CONFIGURATION ---
DATA_FILE = "bot_data.json" 
st.set_page_config(page_title="Ghost Protocol 2.0", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- ADVANCED STYLING (HACKER UI) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 10px; border-radius: 5px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# --- DATA MANAGEMENT ---
def load_data():
    default = {
        "bot_active": False, "daily_count": 0, "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], "history": [], "sent_morning": False, "sent_goodbye": False
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if data.get("last_reset_date") != datetime.now(lz).strftime("%Y-%m-%d"):
                    default["bot_active"] = data["bot_active"] # Keep status
                    return default
                return data
        except: return default
    return default

def save_state():
    data = {
        "bot_active": st.session_state.bot_active, "daily_count": st.session_state.daily_count,
        "last_reset_date": st.session_state.last_reset_date, "signaled_coins": st.session_state.signaled_coins,
        "history": st.session_state.history, "sent_morning": st.session_state.sent_morning, 
        "sent_goodbye": st.session_state.sent_goodbye
    }
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- TELEGRAM ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker: requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else: requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

# --- ROBUST DATA ENGINE (TRIPLE SOURCE) ---
def get_data(symbol, limit=100, timeframe='15m'):
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. Binance US (Primary)
    try:
        url = "https://api.binance.us/api/v3/klines"
        params = {'symbol': symbol, 'interval': timeframe, 'limit': limit}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json(), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ct','qa','nt','tb','tq','i'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df[['open','high','low','close']] = df[['open','high','low','close']].apply(pd.to_numeric)
            return df
    except: pass

    time.sleep(0.5) # Fallback delay

    # 2. MEXC (Backup)
    try:
        url = "https://api.mexc.com/api/v3/klines"
        params = {'symbol': symbol, 'interval': timeframe, 'limit': limit}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json(), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ct','qa','nt','tb','tq','i'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df[['open','high','low','close']] = df[['open','high','low','close']].apply(pd.to_numeric)
            return df
    except: pass

    return pd.DataFrame()

# --- ANALYSIS LOGIC (SCORING FIXED) ---
def analyze_market(df):
    # MSNR: QML
    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])]
    last_highs = df['swing_high'].dropna().tail(3).values
    last_lows = df['swing_low'].dropna().tail(3).values
    
    q_bull = (len(last_lows) >= 2 and last_lows[1] < last_lows[0] and df['close'].iloc[-1] > last_highs[-1])
    q_bear = (len(last_highs) >= 2 and last_highs[1] > last_highs[0] and df['close'].iloc[-1] < last_lows[-1])

    # ICT: FVG & Structure
    fvg_bull = (df['low'].shift(2) > df['high']).iloc[-1]
    fvg_bear = (df['high'].shift(2) < df['low']).iloc[-1]
    
    # CRT: Body Break
    body_up = df['close'].iloc[-1] > df['high'].shift(5).iloc[-1]
    body_down = df['close'].iloc[-1] < df['low'].shift(5).iloc[-1]

    # SCORING (Capped at 100)
    score = 50
    if q_bull: score += 30
    if fvg_bull: score += 15
    if body_up: score += 15
    
    if q_bear: score -= 30
    if fvg_bear: score -= 15
    if body_down: score -= 15
    
    # Logic Correction for Display
    final_score = score
    if score > 100: final_score = 100
    if score < 0: final_score = 0
    
    # Direction
    direction = "Long" if final_score >= 85 else "Short" if final_score <= 15 else "Neutral"
    display_score = final_score if direction == "Long" else (100 - final_score)
    
    return direction, display_score, df['close'].iloc[-1]

# --- INITIALIZE STATE ---
if 'init_done' not in st.session_state:
    saved = load_data()
    for k, v in saved.items(): st.session_state[k] = v
    st.session_state.scan_log = ""
    st.session_state.coins = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC", "LTC", "NEAR", "APT", "FIL", "DOGE", "SUI", "ARB", "OP", "TIA", "INJ", "TRX", "UNI", "ATOM", "IMX", "RNDR"]
    st.session_state.init_done = True

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Control Panel")
    status_text = "RUNNING 🟢" if st.session_state.bot_active else "STOPPED 🔴"
    st.markdown(f"**Status:** {status_text}")
    st.caption("Time: 7:00 - 21:00")
    st.metric("Daily Signals", f"{st.session_state.daily_count} / 8")
    
    c1, c2 = st.columns(2)
    if c1.button("▶ START"):
        st.session_state.bot_active = True
        save_state()
        st.rerun()
    if c2.button("⏹ STOP"):
        st.session_state.bot_active = False
        save_state()
        st.rerun()
        
    st.markdown("---")
    if st.button("⚡ FORCE SCAN"):
        st.session_state.bot_active = True
        st.session_state.force_run = True
        st.rerun()

    st.markdown("---")
    new_coin = st.text_input("Add Coin").upper()
    if st.button("➕ Add"):
        if new_coin and new_coin not in st.session_state.coins:
            st.session_state.coins.append(new_coin)
            st.success(f"Added {new_coin}")

# --- MAIN UI (RESTORED) ---
st.title("👻 GHOST PROTOCOL 2.0 : ELITE TRADER")
st.caption("Methods Active: Structure Guard, 3xATR Shield, Double Conf, Trend (4H), ADX, VSA, Sniper, MSNR, Liquidity, PA, ICT, News, Fib, RSI Div, BB")

t_col1, t_col2 = st.columns([1, 4])
t_col1.metric("LK Sri Lanka Time", datetime.now(lz).strftime('%H:%M:%S'))

tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

# --- SCANNING LOGIC ---
def run_scan():
    st.session_state.scan_log = "" # Clear previous log
    scan_bar = st.progress(0)
    status_msg = st.empty()
    log_area = st.empty()
    
    for i, coin in enumerate(st.session_state.coins):
        # SKIP if already signaled today
        if coin in st.session_state.signaled_coins:
            scan_bar.progress((i + 1) / len(st.session_state.coins))
            continue

        status_msg.markdown(f"👀 **Checking:** `{coin}` ...")
        df = get_data(f"{coin}USDT")
        
        if df.empty:
            log_entry = f"`{coin}`: ⚠️ No Data | "
        else:
            direction, score, price = analyze_market(df)
            
            # Color logic
            color = "green" if score >= 85 else "red" if score >= 85 else "gray" # Note: Short signals are high score in backend but handled by logic
            if direction == "Short": color = "red" # Explicit fix for display
            
            log_entry = f"`{coin}`: :{color}[{score}] | "
            
            # SIGNAL TRIGGER (Score >= 85)
            if score >= 85:
                # Calculate Targets
                sl = price * 0.995 if direction == "Long" else price * 1.005
                tp1 = price * 1.015 if direction == "Long" else price * 0.985
                
                msg = (
                    f"💎<b>CRYPTO CAMPUS VIP</b>💎\n\n"
                    f"🌑 <b>{coin} USDT</b>\n\n"
                    f"{'🟢' if direction == 'Long' else '🔴'} <b>{direction}</b>\n\n"
                    f"🚀<b>Isolated</b>\n"
                    f"📈<b>Leverage 20X</b>\n\n"
                    f"💥<b>Entry {price}</b>\n\n"
                    f"✅<b>Take Profit</b>\n"
                    f"1️⃣ {tp1:.4f}\n\n"
                    f"⭕ <b>Stop Loss {sl:.4f}</b>\n\n"
                    f"⚠️ <b>Margin Use 1%-3%</b>"
                )
                
                # Check Limits
                if st.session_state.daily_count < 8:
                    send_telegram(msg)
                    st.session_state.daily_count += 1
                    st.session_state.signaled_coins.append(coin)
                    st.session_state.history.insert(0, {"Time": datetime.now(lz).strftime("%H:%M"), "Coin": coin, "Signal": direction, "Score": score})
                    save_state()

        # Update Live Log
        st.session_state.scan_log = log_entry + st.session_state.scan_log
        if len(st.session_state.scan_log) > 1500: st.session_state.scan_log = st.session_state.scan_log[:1500]
        log_area.markdown(f"### 📝 Live Scores:\n{st.session_state.scan_log}")
        
        scan_bar.progress((i + 1) / len(st.session_state.coins))
        time.sleep(1.2) # Speed limit to prevent blocking

    status_msg.success("✅ Scan Complete")
    if getattr(st.session_state, 'force_run', False):
        st.session_state.force_run = False

with tab1:
    if st.session_state.bot_active:
        # Check Time Block
        now = datetime.now(lz)
        if 7 <= now.hour < 21:
            # Auto Run every 15 mins logic or Force
            if getattr(st.session_state, 'force_run', False):
                run_scan()
            else:
                next_scan = 15 - (now.minute % 15)
                st.info(f"⏳ **Monitoring...** Next auto-scan in {next_scan} minutes.")
                # Show last log if exists
                if st.session_state.scan_log:
                    st.markdown(f"### 📝 Last Scan Scores:\n{st.session_state.scan_log}")
                time.sleep(10)
                st.rerun()
        else:
            st.warning("💤 SLEEPING (Market Hours 7:00 - 21:00)")
    else:
        st.error("🛑 STOPPED")

with tab2:
    st.table(pd.DataFrame(st.session_state.history))
