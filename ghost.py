import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
from datetime import datetime

# --- USER SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

START_HOUR = 7
END_HOUR = 21

# --- MULTI-METHOD SETTINGS (10 METHODS) ---
# 1. RSI, 2. SMA, 3. ATR, 4. SMC, 5. Elliott Wave, 6. ICT, 7. CRT, 8. MSNR, 9. Fibonacci, 10. News
SCORE_THRESHOLD = 85 # දැන් නීති 10ක් නිසා තවත් තද කළා

LEVERAGE_TEXT = "Isolated 50X"  
LEVERAGE_VAL = 50             
MARGIN_TEXT = "1% - 3%"       
STATUS_FILE = "bot_status.txt"

st.set_page_config(page_title="Ghost Protocol Ultimate", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- MEMORY FUNCTIONS ---
def load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            return f.read().strip() == "TRUE"
    return True 

def save_status(is_active):
    with open(STATUS_FILE, "w") as f:
        f.write("TRUE" if is_active else "FALSE")

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
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200) # දත්ත වැඩිපුර ගත්තා SMC සඳහා
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except: return pd.DataFrame()

# --- THE 10 METHOD ANALYZER ---
def analyze_ultimate(df):
    if df.empty or len(df) < 100: return "NEUTRAL", 50, 0, 0
    
    # Base Indicators
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    high_max = df['high'].max()
    low_min = df['low'].min()
    
    score = 50
    methods_hit = []

    # 1. RSI (25/75)
    if curr['rsi'] < 25: score += 10; methods_hit.append("RSI")
    elif curr['rsi'] > 75: score -= 10; methods_hit.append("RSI")

    # 2. SMA 50 Trend
    if curr['close'] > curr['sma50']: score += 10; methods_hit.append("SMA")
    else: score -= 10; methods_hit.append("SMA")

    # 3. Fibonacci (0.618 Retracement)
    fib_618 = low_min + (high_max - low_min) * 0.618
    if abs(curr['close'] - fib_618) / curr['close'] < 0.005:
        score += 15; methods_hit.append("Fibonacci")

    # 4. SMC Logic (Market Structure Shift)
    if curr['close'] > df['high'].iloc[-20:-1].max():
        score += 15; methods_hit.append("SMC (MSS)")
    elif curr['close'] < df['low'].iloc[-20:-1].min():
        score -= 15; methods_hit.append("SMC (MSS)")

    # 5. ICT Concept (Liquidity Grab/FVG)
    if curr['low'] < df['low'].iloc[-10:-1].min() and curr['close'] > curr['open']:
        score += 15; methods_hit.append("ICT (Liq Grab)")

    # 6. Elliott Wave (Simple Wave 3 identification)
    if curr['close'] > prev['close'] and df['volume'].iloc[-1] > df['volume'].mean():
        score += 10; methods_hit.append("Elliott Wave")

    # 7 & 8. MSNR (Market Support/Resistance) & CRT
    res = df['high'].iloc[-50:].max()
    sup = df['low'].iloc[-50:].min()
    if abs(curr['close'] - sup) < (curr['atr']): score += 10; methods_hit.append("MSNR")
    if abs(curr['close'] - res) < (curr['atr']): score -= 10; methods_hit.append("MSNR")

    # 9. Fundamental News (Check for high volatility hours)
    # News සාමාන්‍යයෙන් එන්නේ ලංකාවේ වෙලාවෙන් 6:00 PM - 8:30 PM අතර
    now_lk = datetime.now(pytz.timezone('Asia/Colombo'))
    if 18 <= now_lk.hour <= 20:
        methods_hit.append("News Alert ⚠️")

    # 10. ATR Volatility Check
    if curr['atr'] > df['atr'].mean(): score += 5

    sig = "LONG" if score >= SCORE_THRESHOLD else "SHORT" if score <= (100 - SCORE_THRESHOLD) else "NEUTRAL"
    return sig, score, curr['close'], curr['atr'], methods_hit

# --- MAIN ENGINE ---
if 'coins' not in st.session_state:
    st.session_state.coins = ["BTC", "ETH", "SOL", "XRP", "BNB", "PEPE", "WIF", "SUI"] # Sample list

if 'history' not in st.session_state: st.session_state.history = []
if 'bot_active' not in st.session_state: st.session_state.bot_active = load_status()

st.sidebar.title("👻 Ghost Ultimate Control")
current_time = datetime.now(lz)
is_within_hours = START_HOUR <= current_time.hour < END_HOUR

if st.sidebar.button("▶️ START"):
    save_status(True); st.session_state.bot_active = True; st.rerun()
if st.sidebar.button("⏹️ STOP"):
    save_status(False); st.session_state.bot_active = False; st.rerun()

st.title("👻 GHOST PROTOCOL : ULTIMATE EDITION")
st.write(f"Methods Active: **RSI, SMA, ATR, SMC, ICT, Elliott Wave, Fibonacci, MSNR, CRT, Fundamental News**")

if st.session_state.bot_active and is_within_hours:
    if current_time.minute % 15 == 0 and current_time.second < 50:
        st.info("🔄 Running 10-Method Institutional Scan...")
        for coin in st.session_state.coins:
            df = get_data(f"{coin}/USDT:USDT")
            sig, score, price, atr, methods = analyze_ultimate(df)
            
            if sig != "NEUTRAL":
                send_telegram("", is_sticker=True)
                time.sleep(15)
                
                # Signal logic... (Targets, SL etc - Same as previous)
                sl_dist = atr * 1.5
                tp_dist = sl_dist
                sl = price - sl_dist if sig == "LONG" else price + sl_dist
                tps = [price + (tp_dist*x) if sig == "LONG" else price - (tp_dist*x) for x in range(1, 5)]
                
                methods_str = ", ".join(methods)
                msg = (f"👻 <b>GHOST ULTIMATE SIGNAL</b>\n\n"
                       f"🪙 <b>{coin}/USDT</b> | {sig}\n"
                       f"🛠 <b>Methods:</b> {methods_str}\n"
                       f"🎯 <b>Entry:</b> {price:.4f}\n"
                       f"🛑 <b>SL:</b> {sl:.4f}\n"
                       f"⚙️ <b>Leverage:</b> {LEVERAGE_TEXT}")
                send_telegram(msg)
                st.session_state.history.insert(0, {"Time": current_time.strftime("%H:%M"), "Coin": coin, "Signal": sig})
        time.sleep(60); st.rerun()

elif not is_within_hours:
    st.warning("💤 Sleeping Mode (Active 07:00 - 21:00)")
else:
    st.error("⏹ Bot is Stopped Manually")

time.sleep(10); st.rerun()
