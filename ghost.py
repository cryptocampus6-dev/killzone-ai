import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import yfinance as yf
# matplotlib and mplfinance removed as chart generation for vision is no longer needed
from datetime import datetime

# ==============================================================================
# 🔐 USER SETTINGS (NO API KEY NEEDED NOW)
# ==============================================================================
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003534299054"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

START_HOUR = 7   
END_HOUR = 21    
MAX_DAILY_SIGNALS = 8
DATA_FILE = "bot_data.json"
RISK_PER_TRADE_ROI = 60 

st.set_page_config(page_title="GHOST x LOGIC 🚀", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- DATA MANAGEMENT ---
def load_data():
    default_coins = [
        "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "LTC", 
        "DOT", "MATIC", "UNI", "BCH", "FIL", "NEAR", "ATOM", "ICP", "IMX", "APT",
        "SUI", "OP", "ARB", "INJ", "RNDR", "STX", "GRT", "VET", "THETA", "RUNE",
        "EGLD", "SAND", "MANA", "AXS", "AAVE", "ALGO", "FTM", "FLOW", "SNX", "KAS",
        "TIA", "SEI", "ORDI", "BONK", "WIF", "PEPE", "FLOKI", "SHIB", "MEME", "1000SATS",
        "FET", "AGIX", "OCEAN", "WLD", "JUP", "PYTH", "BLUR", "DYDX", "GMX", "CRV",
        "LDO", "MKR", "COMP", "FXS", "PENDLE", "ENS", "MINA", "QNT", "HBAR", "EOS",
        "XTZ", "KAVA", "GALA", "CHZ", "IOTA", "NEO", "ZEC", "DASH", "XMR", "ETC",
        "KLAY", "APE", "ZIL", "GMT", "CAKE", "ROSE", "TWT", "LUNC", "GAS", "TRB",
        "LOOM", "BIGTIME", "BLZ", "TRX", "HFT", "MAGIC", "RDNT", "SSV", "ID", "EDU",
        "MAV", "ARKM", "CYBER", "YGG", "API3", "STORJ", "ILV", "BEAM", "VANRY", "STRK",
        "PIXEL", "ALT", "MANTA", "XAI", "AI", "NFP", "ACE", "JTO", "ETHFI", "ENA"
    ]

    default = {
        "bot_active": True, "daily_count": 0, "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], "history": [], "last_scan_block_id": -1,
        "sent_morning": False, "sent_goodbye": False, "scan_log": "", "force_scan": False,
        "coins": default_coins
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                # Ensure missing keys are added from default
                for key, value in default.items():
                    if key not in data:
                        data[key] = value
                
                if data.get("last_reset_date") != datetime.now(lz).strftime("%Y-%m-%d"):
                    data.update({
                        "daily_count": 0, 
                        "signaled_coins": [], 
                        "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"), 
                        "sent_morning": False, 
                        "sent_goodbye": False, 
                        "scan_log": ""
                    })
                    with open(DATA_FILE, "w") as fw: json.dump(data, fw)
                if len(data.get("coins", [])) < 50:
                    data["coins"] = default_coins
                    with open(DATA_FILE, "w") as fw: json.dump(data, fw)
                return data
        except: return default
    return default

def save_full_state():
    # Explicitly save all keys to avoid missing attribute errors
    serializable_data = {k: v for k, v in st.session_state.items() if k in [
        "bot_active", "daily_count", "last_reset_date", "signaled_coins", 
        "history", "last_scan_block_id", "sent_morning", "sent_goodbye", 
        "scan_log", "force_scan", "coins"
    ]}
    with open(DATA_FILE, "w") as f: json.dump(serializable_data, f)

# --- TELEGRAM ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else:
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

# --- DATA FETCHING ---
def get_data(symbol):
    try:
        ticker = f"{symbol}-USD"
        # Increased period to 5d to ensure enough data for indicators
        df = yf.download(ticker, period="5d", interval="15m", progress=False) 
        if df.empty: return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df.columns = [str(c) for c in df.columns]
        if 'Datetime' in df.columns: df = df.rename(columns={'Datetime': 'Date'})
        elif 'index' in df.columns: df = df.rename(columns={'index': 'Date'}) # Handle different index names
        if 'Date' in df.columns: df = df.set_index('Date')
        
        # Numeric Check
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for c in cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
            
        return df.dropna()
    except: return pd.DataFrame()

# ==============================================================================
# 🧠 LOGIC ENGINE (Replaces AI Vision)
# ==============================================================================
# AI ඇහැ ඉවත් කර, ගණිතමය මොළය (Logic) සවි කරන ලදී.
def analyze_with_vision(df, coin_name):
    # Ensure enough data for calculation
    if len(df) < 200: return "NEUTRAL", 0, 0, 0, 0, 0, "Not enough data", None

    # 1. Indicators ගණනය කිරීම
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    
    # 2. අන්තිම අගයන් ගැනීම
    curr_close = df['Close'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    
    # EMA 200 නැත්නම් Current price එකම ගන්න (Error නොවෙන්න)
    ema_200 = df['EMA_200'].iloc[-1] if 'EMA_200' in df.columns and pd.notna(df['EMA_200'].iloc[-1]) else curr_close
    
    # 3. Logic (Trade Strategy)
    sig = "NEUTRAL"
    score = 0
    reason = "Market Choppy"

    # LONG Condition
    if curr_close > ema_200:
        if rsi < 40:
            sig = "LONG"; score = 90; reason = "Trend Pullback (RSI Oversold)"
        elif rsi > 55 and rsi < 70:
            sig = "LONG"; score = 80; reason = "Bullish Momentum"
            
    # SHORT Condition
    elif curr_close < ema_200:
        if rsi > 60:
            sig = "SHORT"; score = 90; reason = "Trend Pullback (RSI Overbought)"
        elif rsi < 45 and rsi > 30:
            sig = "SHORT"; score = 80; reason = "Bearish Momentum"

    # 4. Stop Loss & Leverage
    # ATR සරලව ගණනය කිරීම (High - Low)
    atr_val = df['High'].iloc[-1] - df['Low'].iloc[-1]
    sl = curr_close - (atr_val * 2) if sig == "LONG" else curr_close + (atr_val * 2)
    leverage = 20

    # Return Format එක පරණ එකමයි (කිසිම වෙනසක් නෑ Dashboard එකට)
    return sig, score, curr_close, leverage, sl, 0, reason, None

def format_vip_message(coin, sig, price, sl, tps, leverage):
    p_fmt = ".4f" if price < 50 else ".2f"
    roi_1 = round(abs(tps[0]-price)/price*100*leverage, 1)
    sl_roi = round(abs(price-sl)/price*100*leverage, 1)
    risk = abs(price - sl); reward = abs(tps[3] - price)
    rr = round(reward / risk, 1) if risk > 0 else 0
    direction_text = "🟢Long" if sig == "LONG" else "🔴Short"

    msg = (
        f"💎<b>CRYPTO CAMPUS VIP (5-D FUSION)</b>💎\n\n"
        f"🌟 <b>{coin} USDT</b>\n\n"
        f"{direction_text}\n"
        f"🚀<b>Isolated</b> | 📈<b>Leverage {leverage}X</b>\n\n"
        f"💥<b>Entry {price:{p_fmt}}</b>\n\n"
        f"✅<b>Take Profit</b>\n"
        f"1️⃣ {tps[0]:{p_fmt}} ({roi_1}%)\n"
        f"⭕ <b>Stop Loss {sl:{p_fmt}} ({sl_roi}%)</b>\n\n"
        f"📝 <b>RR 1:{rr}</b>"
    )
    return msg

# ==============================================================================
# MAIN UI
# ==============================================================================
saved_data = load_data()
# Explicitly initialize session state variables to prevent AttributeError
for k, v in saved_data.items():
    if k not in st.session_state: st.session_state[k] = v

# Ensure critical flags exist in session state even if load_data didn't set them
if "sent_goodbye" not in st.session_state: st.session_state.sent_goodbye = False
if "sent_morning" not in st.session_state: st.session_state.sent_morning = False
if "force_scan" not in st.session_state: st.session_state.force_scan = False
if "last_scan_block_id" not in st.session_state: st.session_state.last_scan_block_id = -1

st.sidebar.title("🎛️ Control Panel")
current_time = datetime.now(lz)
is_within_hours = START_HOUR <= current_time.hour < END_HOUR

status_color = "green"; status_text = "RUNNING 🟢" if st.session_state.bot_active else "STOPPED 🔴"
st.sidebar.markdown(f"**Status:** :{status_color}[{status_text}]")
st.sidebar.metric("Daily Signals", f"{st.session_state.daily_count} / {MAX_DAILY_SIGNALS}")

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START", use_container_width=True): st.session_state.bot_active = True; save_full_state(); st.rerun()
if col2.button("⏹️ STOP", use_container_width=True): st.session_state.bot_active = False; save_full_state(); st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚡ FORCE SCAN NOW", use_container_width=True): st.session_state.force_scan = True; st.rerun()
if st.sidebar.button("🔄 RESET LIMIT (Admin)", use_container_width=True):
    st.session_state.daily_count = 0; st.session_state.signaled_coins = []; st.session_state.sent_goodbye = False; st.session_state.sent_morning = False; save_full_state(); st.rerun()

st.sidebar.subheader("🪙 Coin Manager (120 Coins)")
new_coin = st.sidebar.text_input("Add Coin", "").upper()
if st.sidebar.button("➕ Add Coin"):
    if new_coin and new_coin not in st.session_state.coins: st.session_state.coins.append(new_coin); save_full_state(); st.rerun()
rem_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove"):
    if rem_coin in st.session_state.coins: st.session_state.coins.remove(rem_coin); save_full_state(); st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📡 Test 5-D Signal + Sticker", use_container_width=True):
    st.sidebar.info("Sending Sticker & Signal...")
    send_telegram("", is_sticker=True)
    time.sleep(1)
    test_df = get_data("BTC")
    if not test_df.empty:
        price = test_df['Close'].iloc[-1]
        sl = price * 0.995; risk = abs(price - sl)
        tps = [price+risk*1.5, price+risk*3, price+risk*5, price+risk*8]
        msg = format_vip_message("BTC", "LONG", price, sl, tps, 50)
        send_telegram(msg)
        st.sidebar.success("Process Complete. Check Telegram!")

st.title("👻 GHOST x LOGIC 🚀")
st.metric("🇱🇰 Sri Lanka Time", current_time.strftime("%H:%M:%S"))

tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

def run_scan():
    if st.session_state.daily_count >= MAX_DAILY_SIGNALS: return
    if st.session_state.sent_goodbye: return

    st.markdown(f"### 👁️ AI Scanning {len(st.session_state.coins)} Coins...")
    progress_bar = st.progress(0); status_area = st.empty()

    for i, coin in enumerate(st.session_state.coins):
        if coin in st.session_state.signaled_coins: continue
        status_area.markdown(f"📸 **Capturing:** `{coin}` ...")
        df = get_data(coin)
        if df.empty: continue 

        # මෙතන දැන් කතා කරන්නේ අලුත් Logic Engine එකට
        sig, score, price, leverage, sl, _, reason, _ = analyze_with_vision(df, coin)
        
        if sig != "NEUTRAL":
            status_area.markdown(f"🚀 **SIGNAL FOUND:** `{coin}` | Score: **{score}%**")
            send_telegram("", is_sticker=True)
            time.sleep(2)
            risk = abs(price - sl)
            tps = [price+risk*1.5, price+risk*3, price+risk*5, price+risk*8] if sig == "LONG" else [price-risk*1.5, price-risk*3, price-risk*5, price-risk*8]
            msg = format_vip_message(coin, sig, price, sl, tps, leverage)
            send_telegram(msg)
            st.session_state.history.insert(0, {"Time": datetime.now(lz).strftime("%H:%M"), "Coin": coin, "Signal": sig})
            st.session_state.daily_count += 1; st.session_state.signaled_coins.append(coin); save_full_state()
            if st.session_state.daily_count >= MAX_DAILY_SIGNALS:
                status_area.info("🛑 Daily Limit Reached! Waiting 15 mins to send Goodbye...")
                time.sleep(900) 
                send_telegram("🚀 Good Bye Traders! අදට Signals දීලා ඉවරයි. අපි ආයිත් හෙට දවසේ සුපිරි Entries ටිකක් ගමු! 👋")
                st.session_state.sent_goodbye = True; save_full_state(); break
        else:
            status_area.markdown(f"👀 **Scanned:** `{coin}` | Result: {sig} ({score}%) | 📝 {reason}")
        
        time.sleep(1); progress_bar.progress((i + 1) / len(st.session_state.coins))
    st.rerun()

with tab1:
    if st.session_state.bot_active:
        if current_time.hour == START_HOUR and not st.session_state.sent_morning:
            send_telegram("☀️ Good Morning Traders! ඔයාලා හැමෝටම ජයග්‍රාහී සුබ දවසක් වේවා! 🚀")
            st.session_state.sent_morning = True; save_full_state()

        if current_time.hour >= END_HOUR:
            if not st.session_state.sent_goodbye:
                send_telegram("🚀 Good Night Traders! අදට Signals දීලා ඉවරයි. 👋")
                st.session_state.sent_goodbye = True; save_full_state()
            st.warning("💤 AI Sleeping... (Day Ended)"); time.sleep(60); st.rerun()

        elif is_within_hours:
            if not st.session_state.sent_goodbye:
                curr_block = current_time.hour * 4 + (current_time.minute // 15)
                if (curr_block != st.session_state.last_scan_block_id) or st.session_state.force_scan:
                    st.session_state.last_scan_block_id = curr_block; st.session_state.force_scan = False; save_full_state(); run_scan()
                else: st.info("⏳ AI is watching... Next scan in 15 mins."); time.sleep(10); st.rerun()
            else: st.warning("💤 Day Ended (Limit Reached)."); time.sleep(10); st.rerun()
        else: st.warning("💤 AI Sleeping... (Waiting for 07:00)"); time.sleep(10); st.rerun()
    else: st.error("⚠️ AI STOPPED")

with tab2:
    if st.session_state.history: st.table(pd.DataFrame(st.session_state.history))
    else: st.info("No signals yet.")
