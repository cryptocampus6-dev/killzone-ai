import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import yfinance as yf
from datetime import datetime

# ==============================================================================
# 🔐 USER SETTINGS
# ==============================================================================
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

START_HOUR = 7   
END_HOUR = 21    
MAX_DAILY_SIGNALS = 8
DATA_FILE = "bot_data.json"
RISK_PER_TRADE_ROI = 60 

st.set_page_config(page_title="GHOST ALGO V1 🚀", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- DATA MANAGEMENT ---
def load_data():
    default_coins = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "LTC"]
    default = {
        "bot_active": False, "daily_count": 0, "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], "history": [], "coins": default_coins
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return default
    return default

def save_full_state():
    serializable_data = {k: v for k, v in st.session_state.items() if k in ["bot_active", "daily_count", "last_reset_date", "signaled_coins", "history", "coins"]}
    with open(DATA_FILE, "w") as f: json.dump(serializable_data, f)

# --- TELEGRAM ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker: requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else: requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

# --- DATA FETCHING ---
def get_data(symbol):
    try:
        ticker = f"{symbol}-USD"
        # අපි Indicators හදන්න පරණ ඩේටා ටිකක් වැඩිපුර ගමු (Period 5d)
        df = yf.download(ticker, period="5d", interval="15m", progress=False) 
        if df.empty: return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df.columns = [str(c) for c in df.columns]
        if 'Datetime' in df.columns: df = df.rename(columns={'Datetime': 'Date'})
        if 'Date' in df.columns: df = df.set_index('Date')
        
        # Numeric conversion
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for c in cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
            
        return df.dropna()
    except: return pd.DataFrame()

# ==============================================================================
# 🧠 TECHNICAL ANALYSIS ENGINE (NO AI - PURE LOGIC)
# ==============================================================================
def analyze_market_structure(df, coin):
    # 1. Indicators ගණනය කිරීම
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['EMA_50'] = ta.ema(df['Close'], length=50)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    
    current_price = df['Close'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    ema_50 = df['EMA_50'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    
    signal = "NEUTRAL"
    reason = "Consolidation"
    score = 0

    # 2. STRATEGY: Trend Pullback (Trend එකත් එක්ක යන Strategy එකක්)
    
    # --- LONG LOGIC ---
    # Trend එක UP (Price > EMA 200) සහ RSI එක Oversold වෙලා ආයේ හැරෙනකොට (RSI < 40)
    if current_price > ema_200:
        if rsi < 40:
            signal = "LONG"
            score = 85
            reason = "Uptrend Pullback (RSI Oversold)"
        elif current_price > ema_50 and rsi > 50:
            # Strong Uptrend Momentum
            signal = "LONG"
            score = 75
            reason = "Strong Momentum Breakout"
            
    # --- SHORT LOGIC ---
    # Trend එක DOWN (Price < EMA 200) සහ RSI එක Overbought වෙලා ආයේ හැරෙනකොට (RSI > 60)
    elif current_price < ema_200:
        if rsi > 60:
            signal = "SHORT"
            score = 85
            reason = "Downtrend Pullback (RSI Overbought)"
        elif current_price < ema_50 and rsi < 50:
             # Strong Downtrend Momentum
            signal = "SHORT"
            score = 75
            reason = "Strong Bearish Momentum"

    # Stop Loss & Take Profit Calculation
    atr = (df['High'].iloc[-1] - df['Low'].iloc[-1]) # Simple ATR approximation
    if signal == "LONG":
        sl = current_price - (atr * 2)
    else:
        sl = current_price + (atr * 2)
        
    return signal, score, current_price, sl, reason

# ==============================================================================
# MAIN UI (PHOTO 2 DESIGN)
# ==============================================================================
saved_data = load_data()
for k, v in saved_data.items():
    if k not in st.session_state: st.session_state[k] = v

st.sidebar.title("🎛️ Control Panel")
status_color = "green" if st.session_state.bot_active else "red"
st.sidebar.markdown(f"Status: **:{status_color}[{'RUNNING' if st.session_state.bot_active else 'STOPPED'}]**")
st.sidebar.metric("Daily Signals", f"{st.session_state.daily_count} / {MAX_DAILY_SIGNALS}")

if st.sidebar.button("▶️ START", use_container_width=True): 
    st.session_state.bot_active = True
    save_full_state()
    st.rerun()
if st.sidebar.button("⏹️ STOP", use_container_width=True): 
    st.session_state.bot_active = False
    save_full_state()
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚡ FORCE SCAN NOW", use_container_width=True): st.rerun()

# --- COIN MANAGER ---
st.sidebar.subheader("Coin Manager")
new_c = st.sidebar.text_input("Add Coin").upper()
if st.sidebar.button("Add"):
    if new_c and new_c not in st.session_state.coins: st.session_state.coins.append(new_c); save_full_state(); st.rerun()
rem_c = st.sidebar.selectbox("Remove", st.session_state.coins)
if st.sidebar.button("Delete"):
    if rem_c in st.session_state.coins: st.session_state.coins.remove(rem_c); save_full_state(); st.rerun()

st.title("👻 GHOST ALGO V1 ✅")
st.markdown(f"LK Sri Lanka Time: **{datetime.now(lz).strftime('%H:%M:%S')}**")

tab1, tab2 = st.tabs(["📊 Algo Scanner", "📜 Signal History"])

with tab1:
    if st.session_state.bot_active:
        st.markdown("### 🧬 Analyzing Market Structure...")
        progress_bar = st.progress(0)
        status_area = st.empty()
        
        for i, coin in enumerate(st.session_state.coins):
            if not st.session_state.bot_active: break
            if coin in st.session_state.signaled_coins: continue
            
            # 1. Scanning Message
            status_area.markdown(f"🔄 **Calculating:** `{coin}` Indicators...")
            
            df = get_data(coin)
            if df.empty: continue
            
            # 2. Logic Analysis (No AI)
            sig, score, price, sl, reason = analyze_market_structure(df, coin)
            
            # 3. Log Result (Photo 2 Style)
            status_area.markdown(f"👀 **Checked:** {coin} | Signal: {sig} ({score}%) | 📊 {reason}")
            
            if sig != "NEUTRAL" and score >= 80:
                send_telegram("", is_sticker=True)
                msg = (f"🚀 **{coin} {sig}**\n"
                       f"💰 Price: {price:.4f}\n"
                       f"🛑 SL: {sl:.4f}\n"
                       f"📝 Strategy: {reason}")
                send_telegram(msg)
                st.session_state.history.insert(0, {"Time": datetime.now(lz).strftime("%H:%M"), "Coin": coin, "Signal": sig})
                st.session_state.daily_count += 1
                st.session_state.signaled_coins.append(coin)
                save_full_state()
                st.rerun()
            
            progress_bar.progress((i + 1) / len(st.session_state.coins))
            time.sleep(0.1) # වේගයෙන් ස්කෑන් කරයි
    else:
        st.info("⚠️ Bot is Stopped. Click START to begin.")

with tab2:
    st.table(pd.DataFrame(st.session_state.history))
