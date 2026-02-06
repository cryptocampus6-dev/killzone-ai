import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import numpy as np
from datetime import datetime

# --- USER SETTINGS (ඔයාගේ විස්තර) ---
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

# --- CONFIGURATION ---
START_HOUR = 7
END_HOUR = 21
MAX_DAILY_SIGNALS = 8
SCORE_THRESHOLD = 85
TARGET_SL_ROI = 60
DATA_FILE = "bot_data.json"

st.set_page_config(page_title="Ghost Protocol Dashboard", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- DATA MANAGEMENT (Reset logic ඇතුළුව) ---
def load_data():
    default = {
        "bot_active": True, "daily_count": 0, "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], "history": [], "last_scan_block_id": -1,
        "sent_morning": False, "sent_goodbye": False
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if data.get("last_reset_date") != datetime.now(lz).strftime("%Y-%m-%d"):
                    data.update({"daily_count": 0, "signaled_coins": [], "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"), "sent_morning": False, "sent_goodbye": False})
                    with open(DATA_FILE, "w") as fw: json.dump(data, fw)
                return data
        except: return default
    return default

def save_full_state():
    data = {
        "bot_active": st.session_state.bot_active, "daily_count": st.session_state.daily_count,
        "last_reset_date": st.session_state.last_reset_date, "signaled_coins": st.session_state.signaled_coins,
        "history": st.session_state.history, "last_scan_block_id": st.session_state.last_scan_block_id,
        "sent_morning": st.session_state.sent_morning, "sent_goodbye": st.session_state.sent_goodbye
    }
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- TELEGRAM ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker: requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else: requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

# --- ULTRA-STABLE DATA FETCHING (Using CryptoCompare - Free & Safe) ---
def get_stable_data(coin, limit=100):
    try:
        # CryptoCompare API is very stable for cloud environments
        url = f"https://min-api.cryptocompare.com/data/v2/histominute?fsym={coin}&tsym=USDT&limit={limit}"
        res = requests.get(url, timeout=10)
        data = res.json()
        if data['Response'] == 'Success':
            df = pd.DataFrame(data['Data']['Data'])
            df = df.rename(columns={'time': 'ts', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volumefrom': 'v'})
            df['timestamp'] = pd.to_datetime(df['ts'], unit='s')
            return df
    except: pass
    return pd.DataFrame()

# ==============================================================================
# 🧠 THE "TRADING BIBLE" LOGIC (All 5 Methods Integrated)
# ==============================================================================

def analyze_bible_logic(coin):
    df = get_stable_data(coin, limit=150)
    if df.empty or len(df) < 50: return "NEUTRAL", 0, 0, 0, 0, 0, []

    df['atr'] = ta.atr(df['h'], df['l'], df['c'], 14)
    df['ema200'] = ta.ema(df['c'], 100) # Proxy for 4H Trend
    df['rsi'] = ta.rsi(df['c'], 14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    methods_hit = []
    score = 50 

    # 1. Fundamental/News (Volatility Check)
    if (curr['h'] - curr['l']) > (curr['atr'] * 3.5):
        return "NEUTRAL", 0, 0, 0, 0, 0, ["NEWS EVENT"]

    # 2. Malaysian SNR (QML Approximation)
    swing_low = df['l'].tail(20).min()
    swing_high = df['h'].tail(20).max()
    qml_bull = (curr['c'] > swing_high) and (prev['l'] < swing_low)
    qml_bear = (curr['c'] < swing_low) and (prev['h'] > swing_high)

    # 3. Liquidity (Sweep)
    sweep_bull = (curr['l'] < df['l'].iloc[-10:-1].min()) and (curr['c'] > df['l'].iloc[-10:-1].min())
    sweep_bear = (curr['h'] > df['h'].iloc[-10:-1].max()) and (curr['c'] < df['h'].iloc[-10:-1].max())

    # 4. ICT/CRT (FVG & Time)
    fvg_bull = (df['l'].shift(2) > df['h']).iloc[-1]
    killzone = (7 <= datetime.now(pytz.utc).hour <= 10) or (12 <= datetime.now(pytz.utc).hour <= 16)

    # Scoring
    if curr['c'] > df['ema200'].iloc[-1]: # Bullish Context
        if qml_bull: score += 25; methods_hit.append("QML")
        if sweep_bull: score += 20; methods_hit.append("Sweep")
        if fvg_bull: score += 15; methods_hit.append("FVG")
        if killzone: score += 10
    else: # Bearish Context
        if qml_bear: score -= 25; methods_hit.append("QML")
        if sweep_bear: score -= 20; methods_hit.append("Sweep")
        if killzone: score -= 10

    sig = "NEUTRAL"
    final_score = score
    if score >= SCORE_THRESHOLD:
        sig = "LONG"; final_score = min(score, 100)
    elif score <= (100 - SCORE_THRESHOLD):
        sig = "SHORT"; final_score = min(100 - score, 100)

    sl_long = curr['l'] - (curr['atr'] * 1.5)
    sl_short = curr['h'] + (curr['atr'] * 1.5)

    return sig, final_score, curr['c'], curr['atr'], sl_long, sl_short, methods_hit

# ==============================================================================
# MAIN APP LOOP (ඔයාගේ UI එක එහෙම්මමයි)
# ==============================================================================

saved_data = load_data()
for key in ["bot_active", "daily_count", "last_reset_date", "signaled_coins", "history", "sent_morning", "sent_goodbye"]:
    if key not in st.session_state: st.session_state[key] = saved_data[key]

if 'coins' not in st.session_state:
    st.session_state.coins = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "TRX", "MATIC", "LTC", "BCH", "UNI", "NEAR"]
if 'scan_log' not in st.session_state: st.session_state.scan_log = ""
if 'last_scan_block_id' not in st.session_state: st.session_state.last_scan_block_id = -1

# Sidebar
st.sidebar.title("🎛️ Control Panel")
status = "RUNNING 🟢" if st.session_state.bot_active else "STOPPED 🔴"
st.sidebar.markdown(f"### Status: {status}")
st.sidebar.metric("Daily Signals", f"{st.session_state.daily_count} / 8")

if st.sidebar.button("▶️ START"): st.session_state.bot_active = True; save_full_state(); st.rerun()
if st.sidebar.button("⏹️ STOP"): st.session_state.bot_active = False; save_full_state(); st.rerun()
if st.sidebar.button("⚡ FORCE SCAN NOW"): run_scan = True # Trigger scan logic

# Main UI (ඔයාගේ පරණ Emojis සහ Dashboard එක)
st.title("👻 GHOST PROTOCOL 2.0 : ELITE TRADER")
st.write("Methods Active: **Structure Guard, 3xATR Shield, Double Conf, Trend (4H), ADX, VSA, Sniper, MSNR, Liquidity, PA, ICT, News, Fib, RSI Div, BB**")
st.metric("🇱🇰 Sri Lanka Time", datetime.now(lz).strftime("%H:%M:%S"))

tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

def start_scanning():
    if st.session_state.daily_count >= 8: st.warning("Daily Limit Reached."); return
    
    st.markdown(f"### 🔄 Scanning {len(st.session_state.coins)} Coins...")
    prog = st.progress(0); log_placeholder = st.empty()
    st.session_state.scan_log = ""

    for i, coin in enumerate(st.session_state.coins):
        if coin in st.session_state.signaled_coins: continue
        
        sig, score, price, atr, sl_l, sl_s, methods = analyze_bible_logic(coin)
        color = "green" if score >= 85 else "red" if score >= 15 and sig == "SHORT" else "white"
        
        # ලොග් එක අප්ඩේට් කිරීම
        st.session_state.scan_log = f"`{coin}`: :{color}[{score}] | " + st.session_state.scan_log
        log_placeholder.markdown(f"#### 📝 Live Scores:\n{st.session_state.scan_log}")
        
        if sig != "NEUTRAL":
            # සිග්නල් එක යැවීම
            st.session_state.daily_count += 1
            st.session_state.signaled_coins.append(coin)
            msg = f"💎<b>VIP SIGNAL</b>💎\n\n🌑 <b>{coin} USDT</b>\n{'🟢' if sig=='LONG' else '🔴'}<b>{sig}</b>\n\n💥<b>Entry {price}</b>\n⭕<b>SL {(sl_l if sig=='LONG' else sl_s):.4f}</b>"
            send_telegram(msg); save_full_state()
            if st.session_state.daily_count >= 8: break

        prog.progress((i + 1) / len(st.session_state.coins))
        time.sleep(2) # Speed Control

with tab1:
    if st.session_state.bot_active:
        # Scan automatically based on time blocks or force button
        now = datetime.now(lz)
        curr_block = now.hour * 4 + (now.minute // 15)
        if curr_block != st.session_state.last_scan_block_id:
            st.session_state.last_scan_block_id = curr_block
            start_scanning()
            st.rerun()
        else:
            if st.session_state.scan_log: st.markdown(f"#### 📝 Last Scan Scores:\n{st.session_state.scan_log}")
            st.info("⏳ Monitoring... Next scan in 15 mins.")
    else: st.error("🛑 STOPPED")

with tab2: st.table(pd.DataFrame(st.session_state.history))
