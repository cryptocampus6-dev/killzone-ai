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
START_HOUR = 7   # උදේ 7
END_HOUR = 21    # රෑ 9

# --- 10 METHODS CONFIG ---
SCORE_THRESHOLD = 85 

# Leverage Settings
LEVERAGE_VAL = 50             
STATUS_FILE = "bot_status.txt"

st.set_page_config(page_title="Ghost Protocol Dashboard", page_icon="👻", layout="wide")
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

# --- TELEGRAM FUNCTION ---
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
        exchange.timeout = 10000 
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except: return pd.DataFrame()

# --- THE 10 METHOD ANALYZER ---
def analyze_ultimate(df):
    if df.empty or len(df) < 100: return "NEUTRAL", 50, 0, 0, []
    
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    high_max = df['high'].max()
    low_min = df['low'].min()
    
    score = 50
    methods_hit = []

    # 1. RSI
    if curr['rsi'] < 25: score += 10; methods_hit.append("RSI")
    elif curr['rsi'] > 75: score -= 10; methods_hit.append("RSI")

    # 2. SMA
    if curr['close'] > curr['sma50']: score += 10; methods_hit.append("SMA")
    else: score -= 10; methods_hit.append("SMA")

    # 3. Fibonacci
    fib_618 = low_min + (high_max - low_min) * 0.618
    if abs(curr['close'] - fib_618) / curr['close'] < 0.005:
        score += 15; methods_hit.append("Fibonacci")

    # 4. SMC
    if curr['close'] > df['high'].iloc[-20:-1].max():
        score += 15; methods_hit.append("SMC (MSS)")
    elif curr['close'] < df['low'].iloc[-20:-1].min():
        score -= 15; methods_hit.append("SMC (MSS)")

    # 5. ICT
    if curr['low'] < df['low'].iloc[-10:-1].min() and curr['close'] > curr['open']:
        score += 15; methods_hit.append("ICT (Liq Grab)")

    # 6. Elliott Wave
    if curr['close'] > prev['close'] and df['volume'].iloc[-1] > df['volume'].mean():
        score += 10; methods_hit.append("Elliott Wave")

    # 7 & 8. MSNR
    res = df['high'].iloc[-50:].max()
    sup = df['low'].iloc[-50:].min()
    if abs(curr['close'] - sup) < (curr['atr']): score += 10; methods_hit.append("MSNR")
    if abs(curr['close'] - res) < (curr['atr']): score -= 10; methods_hit.append("MSNR")

    # 9. News
    now_lk = datetime.now(pytz.timezone('Asia/Colombo'))
    if 18 <= now_lk.hour <= 20:
        methods_hit.append("News Alert ⚠️")

    # 10. ATR
    if curr['atr'] > df['atr'].mean(): score += 5

    sig = "LONG" if score >= SCORE_THRESHOLD else "SHORT" if score <= (100 - SCORE_THRESHOLD) else "NEUTRAL"
    return sig, score, curr['close'], curr['atr'], methods_hit

# --- SESSION STATE (BINANCE FUTURES LIST) ---
if 'coins' not in st.session_state:
    st.session_state.coins = [
        "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "TRX",
        "MATIC", "LTC", "BCH", "UNI", "NEAR", "APT", "ICP", "FIL", "ATOM", "XLM",
        "DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "MEME", "PEOPLE", "BOME",
        "DOGS", "NOT", "TURBO", "BRETT", "POPCAT", "MYRO", "LADYS", "SATS", "ORDI",
        "RENDER", "FET", "WLD", "ARKM", "GRT", "THETA", "AGIX", "OCEAN", "PHB",
        "SUI", "SEI", "ARB", "OP", "TIA", "INJ", "KAS", "TON", "FTM", "ALGO",
        "MANTA", "STRK", "BLUR", "ZRO", "ZK", "PYTH", "JUP", "ENS", "CRV",
        "AAVE", "MKR", "SNX", "COMP", "1INCH", "RUNE", "DYDX", "GMX", "LDO",
        "PENDLE", "EGLD", "SAND", "MANA", "AXS", "GALA", "CHZ", "FLOW", "EOS",
        "NEO", "QTUM", "IOTA", "KAVA", "MINA", "QNT", "HBAR", "VET", "ZEC",
        "DASH", "XMR", "ROSE", "HOT", "RVN", "BAT", "ENJ", "ZIL", "IOST"
    ]

if 'history' not in st.session_state: st.session_state.history = []
if 'bot_active' not in st.session_state: st.session_state.bot_active = load_status()

# --- SIDEBAR ---
st.sidebar.title("🎛️ Control Panel")

coins_list = st.session_state.coins
current_time = datetime.now(lz)
is_within_hours = START_HOUR <= current_time.hour < END_HOUR

if not st.session_state.bot_active:
    status_color = "red"; status_text = "STOPPED 🔴"
elif not is_within_hours:
    status_color = "orange"; status_text = "SLEEPING 💤"
else:
    status_color = "green"; status_text = "RUNNING 🟢"

st.sidebar.markdown(f"### Status: **:{status_color}[{status_text}]**")
st.sidebar.caption(f"Operating Hours: {START_HOUR}:00 - {END_HOUR}:00")

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START"):
    save_status(True); st.session_state.bot_active = True; st.rerun()
if col2.button("⏹️ STOP"):
    save_status(False); st.session_state.bot_active = False; st.rerun()

st.sidebar.markdown("---")

st.sidebar.subheader("🪙 Coin Manager")
new_coin = st.sidebar.text_input("Add Coin (e.g. SUI)", "").upper()
if st.sidebar.button("➕ Add Coin"):
    if new_coin and new_coin not in st.session_state.coins:
        st.session_state.coins.append(new_coin)
        st.success(f"{new_coin} Added!")

remove_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove Selected"):
    if remove_coin in st.session_state.coins:
        st.session_state.coins.remove(remove_coin); st.rerun()

st.sidebar.markdown("---")

# --- FIXED TEST BUTTON (UPDATED EMOJIS) ---
if st.sidebar.button("📡 Test Telegram"):
    send_telegram("", is_sticker=True)
    time.sleep(2)
    
    # Example for Long
    test_msg = (
        f"💎<b>CRYPTO CAMPUS VIP</b>💎\n\n"
        f"🌑 <b>BTC USDT</b>\n\n"
        f"🟢<b>Long</b>\n\n"
        f"🚀<b>Isolated</b>\n"
        f"📈<b>Leverage 50X</b>\n\n"
        f"💥<b>Entry 82000.90</b>\n\n"
        f"✅<b>Take Profit</b>\n\n"
        f"1️⃣ 83000.86 (30.0%)\n"
        f"2️⃣ 84000.67 (60.0%)\n"
        f"3️⃣ 85000.63 (90.0%)\n"
        f"4️⃣ 86000.63 (169.0%)\n\n"
        f"⭕ <b>Stop Loss 81000.674(60.0%)</b>\n\n"
        f"📝 <b>RR 1:5.6</b>\n\n"
        f"⚠️ <b>Margin Use 1%-5%(Trading Plan Use)</b>"
    )
    send_telegram(test_msg)
    st.sidebar.success("Test Sent!")

# --- MAIN DASHBOARD ---
st.title("👻 GHOST PROTOCOL : ULTIMATE EDITION")
st.write("Methods Active: **RSI, SMA, ATR, SMC, ICT, Elliott Wave, Fibonacci, MSNR, CRT, News**")
now_live = current_time.strftime("%H:%M:%S")
st.metric("🇱🇰 Sri Lanka Time", now_live)

tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

with tab1:
    if st.session_state.bot_active:
        if is_within_hours:
            st.success(f"✅ SYSTEM ACTIVE - Scanning Market (Ends at {END_HOUR}:00)")
            
            if current_time.minute % 15 == 0 and current_time.second < 50:
                st.markdown(f"### 🔄 Scanning {len(coins_list)} Coins...")
                progress_bar = st.progress(0)
                
                for i, coin in enumerate(coins_list):
                    try:
                        df = get_data(f"{coin}/USDT:USDT")
                        if not df.empty:
                            sig, score, price, atr, methods = analyze_ultimate(df)
                            
                            if sig != "NEUTRAL":
                                send_telegram("", is_sticker=True)
                                time.sleep(15)
                                
                                sl_dist = atr * 1.5
                                tp_dist = sl_dist
                                
                                # Logic to switch Emojis based on Direction
                                if sig == "LONG":
                                    sl = price - sl_dist
                                    tps = [price + tp_dist*x for x in range(1, 5)] 
                                    emoji_circle = "🟢"
                                    direction_txt = "Long"
                                else:
                                    sl = price + sl_dist
                                    tps = [price - tp_dist*x for x in range(1, 5)]
                                    emoji_circle = "🔴"
                                    direction_txt = "Short"
                                
                                rr = round(abs(tps[3]-price)/abs(price-sl), 2)
                                
                                # ROI Calculations
                                roi_1 = round(abs(tps[0] - price) / price * 100 * LEVERAGE_VAL, 1)
                                roi_2 = round(abs(tps[1] - price) / price * 100 * LEVERAGE_VAL, 1)
                                roi_3 = round(abs(tps[2] - price) / price * 100 * LEVERAGE_VAL, 1)
                                roi_4 = round(abs(tps[3] - price) / price * 100 * LEVERAGE_VAL, 1)
                                sl_roi = round(abs(price - sl) / price * 100 * LEVERAGE_VAL, 1)
                                
                                methods_str = ", ".join(methods)

                                # --- UPDATED MESSAGE FORMAT WITH NEW EMOJIS ---
                                msg = (
                                    f"💎<b>CRYPTO CAMPUS VIP</b>💎\n\n"
                                    f"🌑 <b>{coin} USDT</b>\n\n"
                                    f"{emoji_circle}<b>{direction_txt}</b>\n\n"
                                    f"🚀<b>Isolated</b>\n"
                                    f"📈<b>Leverage 50X</b>\n\n"
                                    f"💥<b>Entry {price:.4f}</b>\n\n"
                                    f"✅<b>Take Profit</b>\n\n"
                                    f"1️⃣ {tps[0]:.4f} ({roi_1}%)\n"
                                    f"2️⃣ {tps[1]:.4f} ({roi_2}%)\n"
                                    f"3️⃣ {tps[2]:.4f} ({roi_3}%)\n"
                                    f"4️⃣ {tps[3]:.4f} ({roi_4}%)\n\n"
                                    f"⭕ <b>Stop Loss {sl:.4f} ({sl_roi}%)</b>\n\n"
                                    f"📝 <b>RR 1:{rr}</b>\n\n"
                                    f"⚠️ <b>Margin Use 1%-5%(Trading Plan Use)</b>"
                                )
                                
                                send_telegram(msg)
                                st.session_state.history.insert(0, {"Time": current_time.strftime("%H:%M"), "Coin": coin, "Signal": sig, "Methods": methods_str})
                    except: pass
                    progress_bar.progress((i + 1) / len(coins_list))
                
                st.success("Scan Complete!")
                time.sleep(60); st.rerun()
            else:
                time.sleep(1)
                if current_time.second % 15 == 0: st.rerun()
        else:
            st.warning(f"💤 SLEEPING MODE (Resumes at {START_HOUR}:00)")
            time.sleep(10); st.rerun()
    else:
        st.error("⚠️ Engine is STOPPED manually.")
        time.sleep(2)

with tab2:
    if st.session_state.history:
        st.table(pd.DataFrame(st.session_state.history))
    else:
        st.info("No signals yet.")
