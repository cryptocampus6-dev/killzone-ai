import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime

# --- USER SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

# --- SIGNAL STRATEGY SETTINGS (STRICT MODE) ---
RSI_LOWER = 25  
RSI_UPPER = 75  
SCORE_THRESHOLD = 80 

LEVERAGE_TEXT = "Isolated 50X"  
LEVERAGE_VAL = 50             
MARGIN_TEXT = "1% - 3%"       

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
    # Strict Logic
    if curr['close'] > curr['sma50']: score += 20
    else: score -= 20
    
    if curr['rsi'] < RSI_LOWER: score += 30 
    elif curr['rsi'] > RSI_UPPER: score -= 30 
    
    sig = "LONG" if score >= SCORE_THRESHOLD else "SHORT" if score <= (100 - SCORE_THRESHOLD) else "NEUTRAL"
    return sig, score, curr['close'], curr['atr']

# --- SESSION STATE ---
if 'coins' not in st.session_state:
    st.session_state.coins = [
        "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "SHIB", "DOT",
        "LINK", "TRX", "MATIC", "BCH", "NEAR", "UNI", "LTC", "APT", "INJ", "OP",
        "ARB", "ETC", "FIL", "ATOM", "IMX", "VET", "HBAR", "XLM", "RENDER", "GRT",
        "ALGO", "STX", "EGLD", "AAVE", "THETA", "FTM", "SAND", "MANA", "AXS", "EOS",
        "XTZ", "FLOW", "KAVA", "GALA", "QNT", "CHZ", "PEPE", "WIF", "BONK", "SUI",
        "SEI", "TIA", "ORDI", "1000SATS", "LDO", "ICP", "JUP", "PYTH", "ENS", "CRV"
    ]

if 'history' not in st.session_state:
    st.session_state.history = []

# AUTO-START: පෙරනිමියෙන්ම ON වේ
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = True

# --- SIDEBAR UI (ඔයා ඉල්ලපු Control Panel එක) ---
st.sidebar.title("🎛️ Control Panel")

# Status
status_color = "green" if st.session_state.bot_active else "red"
status_text = "RUNNING 🟢" if st.session_state.bot_active else "STOPPED 🔴"
st.sidebar.markdown(f"### Status: **:{status_color}[{status_text}]**")

# Start/Stop Buttons
col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START"):
    st.session_state.bot_active = True
    st.rerun()
if col2.button("⏹️ STOP"):
    st.session_state.bot_active = False
    st.rerun()

st.sidebar.markdown("---")

# Coin Manager
st.sidebar.subheader("🪙 Coin Manager")
new_coin = st.sidebar.text_input("Add Coin (e.g. SUI)", "").upper()
if st.sidebar.button("➕ Add"):
    if new_coin and new_coin not in st.session_state.coins:
        st.session_state.coins.append(new_coin)
        st.success(f"{new_coin} Added!")
    elif new_coin in st.session_state.coins:
        st.sidebar.warning("Exists!")

remove_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove"):
    if remove_coin in st.session_state.coins:
        st.session_state.coins.remove(remove_coin)
        st.rerun()

st.sidebar.markdown("---")
# Test Button
if st.sidebar.button("📡 Test Telegram"):
    send_telegram("", is_sticker=True)
    time.sleep(2)
    send_telegram("🔔 <b>Manual Test:</b> Ghost Protocol is Online! 🚀")
    st.sidebar.success("Test Sent!")

# --- MAIN DASHBOARD ---
st.title("👻 GHOST PROTOCOL : HYBRID DASHBOARD")

# Live Clock
now_live = datetime.now(lz).strftime("%H:%M:%S")
st.metric("🇱🇰 Sri Lanka Time", now_live)

# Tabs
tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

with tab1:
    if st.session_state.bot_active:
        st.success("✅ Engine is Running... (Auto-Pilot Mode ON)")
        st.caption("Machine එක Off කළත් UptimeRobot හරහා මෙය ක්‍රියාත්මක වේ.")
        
        placeholder = st.empty()
        current_time = datetime.now(lz)
        
        # Scan Logic (Runs every 15 mins approx)
        if current_time.minute % 15 == 0 and current_time.second < 50:
            placeholder.markdown(f"### 🔄 Scanning Market... ({now_live})")
            progress_bar = st.progress(0)
            
            coins_list = st.session_state.coins
            for i, coin in enumerate(coins_list):
                try:
                    df = get_data(f"{coin}/USDT:USDT")
                    if not df.empty:
                        sig, score, price, atr = analyze(df)
                        
                        if sig != "NEUTRAL":
                            send_telegram("", is_sticker=True)
                            time.sleep(15) # Delay
                            
                            sl_dist = atr * 1.5
                            tp_dist = sl_dist
                            
                            if sig == "LONG":
                                sl = price - sl_dist
                                tps = [price + tp_dist*x for x in range(1, 5)] 
                                emoji = "🟢"
                            else:
                                sl = price + sl_dist
                                tps = [price - tp_dist*x for x in range(1, 5)]
                                emoji = "🔴"
                            
                            rr = round(abs(tps[3]-price)/abs(price-sl), 2)
                            
                            roi_1 = round(abs(tps[0] - price) / price * 100 * LEVERAGE_VAL, 1)
                            roi_2 = round(abs(tps[1] - price) / price * 100 * LEVERAGE_VAL, 1)
                            roi_3 = round(abs(tps[2] - price) / price * 100 * LEVERAGE_VAL, 1)
                            roi_4 = round(abs(tps[3] - price) / price * 100 * LEVERAGE_VAL, 1)
                            sl_roi = round(abs(price - sl) / price * 100 * LEVERAGE_VAL, 1)

                            msg = (f"💎 <b>PREMIUM VIP SIGNAL</b> 💎\n\n"
                                   f"🪙 <b>{coin} / USDT</b>\n"
                                   f"📈 <b>{sig}</b> {emoji}\n"
                                   f"⚙️ <b>{LEVERAGE_TEXT}</b>\n\n"
                                   f"🚪 <b>Entry:</b> {price:.5f}\n\n"
                                   f"💰 <b>Take Profit:</b>\n"
                                   f"1️⃣ {tps[0]:.5f} ({roi_1}%)\n"
                                   f"2️⃣ {tps[1]:.5f} ({roi_2}%)\n"
                                   f"3️⃣ {tps[2]:.5f} ({roi_3}%)\n"
                                   f"4️⃣ {tps[3]:.5f} ({roi_4}%)\n\n"
                                   f"⛔ <b>Stop Loss:</b> {sl:.5f} (-{sl_roi}%)\n\n"
                                   f"⚖️ <b>RR:</b> 1:{rr}\n"
                                   f"🛡️ <b>Margin Use:</b> {MARGIN_TEXT}")
                            
                            send_telegram(msg)
                            
                            log_entry = {
                                "Time": current_time.strftime("%H:%M"),
                                "Coin": coin,
                                "Signal": sig,
                                "Entry": price,
                                "Status": "Sent ✅"
                            }
                            st.session_state.history.insert(0, log_entry)
                    
                    progress_bar.progress((i + 1) / len(coins_list))
                except: pass
            
            st.success("Scan Complete!")
            time.sleep(60)
            st.rerun()
            
        else:
            placeholder.info(f"⏳ Waiting for next scan cycle (Every 15 mins)... Current: {now_live}")
            time.sleep(1)
            if current_time.second % 10 == 0:
                st.rerun()
            
    else:
        st.warning("⚠️ Engine is STOPPED. Click '▶️ START' in sidebar.")

with tab2:
    st.subheader("Recent Signals")
    if st.session_state.history:
        st.table(pd.DataFrame(st.session_state.history))
    else:
        st.info("No signals generated yet.")
