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

# --- TIME SETTINGS ---
START_HOUR = 7
END_HOUR = 21

# --- STRATEGY SETTINGS (10 METHODS) ---
# Methods: 1.RSI, 2.SMA, 3.ATR, 4.SMC, 5.ICT, 6.Elliott, 7.Fibonacci, 8.MSNR, 9.CRT, 10.News
SCORE_THRESHOLD = 85

LEVERAGE_TEXT = "Isolated 50X"  
LEVERAGE_VAL = 50             
MARGIN_TEXT = "1% - 3%"       
STATUS_FILE = "bot_status.txt"

st.set_page_config(page_title="Ghost Ultimate Dashboard", page_icon="👻", layout="wide")
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

# --- TELEGRAM FUNCTIONS ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else:
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
        return True
    except: return False

# --- DATA & ANALYSIS (10 METHODS) ---
def get_data(symbol):
    try:
        exchange = ccxt.mexc({'options': {'defaultType': 'swap'}})
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=150)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except: return pd.DataFrame()

def analyze_ultimate(df):
    if df.empty or len(df) < 100: return "NEUTRAL", 50, 0, 0, []
    
    # 1, 2, 3. RSI, SMA, ATR
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    score = 50
    methods_hit = []

    # Strategy Logic
    if curr['rsi'] < 25: score += 10; methods_hit.append("RSI")
    elif curr['rsi'] > 75: score -= 10; methods_hit.append("RSI")
    
    if curr['close'] > curr['sma50']: score += 10; methods_hit.append("SMA")
    else: score -= 10; methods_hit.append("SMA")

    # 4. SMC MSS Check
    if curr['close'] > df['high'].iloc[-20:-1].max(): score += 15; methods_hit.append("SMC")
    elif curr['close'] < df['low'].iloc[-20:-1].min(): score -= 15; methods_hit.append("SMC")

    # 5. ICT Liquidity
    if curr['low'] < df['low'].iloc[-10:-1].min() and curr['close'] > curr['open']:
        score += 15; methods_hit.append("ICT")

    # 6. Fibonacci 0.618
    fib_618 = df['low'].min() + (df['high'].max() - df['low'].min()) * 0.618
    if abs(curr['close'] - fib_618) / curr['close'] < 0.005:
        score += 10; methods_hit.append("Fibonacci")

    # 7. Elliott Wave Lite
    if curr['close'] > prev['close'] and df['volume'].iloc[-1] > df['volume'].mean():
        score += 5; methods_hit.append("Elliott")

    # 8, 9. MSNR & CRT
    sup = df['low'].iloc[-50:].min()
    res = df['high'].iloc[-50:].max()
    if abs(curr['close'] - sup) < curr['atr']: score += 10; methods_hit.append("MSNR")
    if abs(curr['close'] - res) < curr['atr']: score -= 10; methods_hit.append("CRT")

    # 10. News (Time Based Alert)
    now_lk = datetime.now(lz)
    if 18 <= now_lk.hour <= 21: methods_hit.append("News-High-Vol")

    sig = "LONG" if score >= SCORE_THRESHOLD else "SHORT" if score <= (100 - SCORE_THRESHOLD) else "NEUTRAL"
    return sig, score, curr['close'], curr['atr'], methods_hit

# --- UI & DASHBOARD ---
if 'coins' not in st.session_state:
    st.session_state.coins = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "PEPE", "WIF", "SUI"]
if 'history' not in st.session_state: st.session_state.history = []
if 'bot_active' not in st.session_state: st.session_state.bot_active = load_status()

# Sidebar (Back to Memory Mode Style)
st.sidebar.title("🎛️ Control Panel")
status_color = "green" if st.session_state.bot_active else "red"
st.sidebar.markdown(f"Status: **:{status_color}[{'RUNNING' if st.session_state.bot_active else 'STOPPED'}]**")

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START"):
    save_status(True); st.session_state.bot_active = True; st.rerun()
if col2.button("⏹️ STOP"):
    save_status(False); st.session_state.bot_active = False; st.rerun()

st.sidebar.divider()
st.sidebar.subheader("🪙 Coin Manager")
new_c = st.sidebar.text_input("Add Coin").upper()
if st.sidebar.button("➕ Add"):
    if new_c and new_c not in st.session_state.coins: st.session_state.coins.append(new_c); st.rerun()

rem_c = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove"):
    st.session_state.coins.remove(rem_c); st.rerun()

# Main UI
st.title("👻 GHOST PROTOCOL : ULTIMATE DASHBOARD")
current_time = datetime.now(lz)
st.metric("🇱🇰 Sri Lanka Time", current_time.strftime("%H:%M:%S"))

is_within_hours = START_HOUR <= current_time.hour < END_HOUR

if st.session_state.bot_active:
    if is_within_hours:
        st.success("✅ SYSTEM ACTIVE - Monitoring 10 Analysis Methods")
        if current_time.minute % 15 == 0 and current_time.second < 50:
            st.info("🔄 Institutional Scan in Progress...")
            progress = st.progress(0)
            for i, coin in enumerate(st.session_state.coins):
                df = get_data(f"{coin}/USDT:USDT")
                sig, score, price, atr, methods = analyze_ultimate(df)
                if sig != "NEUTRAL":
                    send_telegram("", is_sticker=True); time.sleep(15)
                    sl = price - (atr*1.5) if sig == "LONG" else price + (atr*1.5)
                    tps = [price + (atr*1.5*x) if sig == "LONG" else price - (atr*1.5*x) for x in range(1, 5)]
                    
                    roi = [round(abs(t - price)/price * 100 * LEVERAGE_VAL, 1) for t in tps]
                    msg = (f"💎 <b>ULTIMATE VIP SIGNAL</b> 💎\n\n"
                           f"🪙 <b>{coin}/USDT</b> | {sig} {'🟢' if sig=='LONG' else '🔴'}\n"
                           f"🛠 <b>Methods:</b> {', '.join(methods)}\n"
                           f"⚙️ <b>{LEVERAGE_TEXT}</b>\n\n"
                           f"🚪 <b>Entry:</b> {price:.5f}\n\n"
                           f"🎯 <b>Targets:</b>\n"
                           f"1️⃣ {tps[0]:.5f} ({roi[0]}%)\n"
                           f"2️⃣ {tps[1]:.5f} ({roi[1]}%)\n"
                           f"3️⃣ {tps[2]:.5f} ({roi[2]}%)\n"
                           f"4️⃣ {tps[3]:.5f} ({roi[3]}%)\n\n"
                           f"⛔ <b>SL:</b> {sl:.5f}\n"
                           f"🛡️ <b>Margin:</b> {MARGIN_TEXT}")
                    send_telegram(msg)
                    st.session_state.history.insert(0, {"Time": current_time.strftime("%H:%M"), "Coin": coin, "Signal": sig, "Methods": len(methods)})
                progress.progress((i+1)/len(st.session_state.coins))
            time.sleep(60); st.rerun()
    else:
        st.warning(f"💤 Sleeping Mode (Active {START_HOUR}:00 - {END_HOUR}:00)")
else:
    st.error("⏹ Engine Stopped Manually")

st.divider()
st.subheader("📜 Recent Signals (Session History)")
if st.session_state.history: st.table(pd.DataFrame(st.session_state.history))
else: st.info("No signals yet.")
time.sleep(10); st.rerun()
