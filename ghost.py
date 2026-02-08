import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import yfinance as yf

# --- FIX: MATPLOTLIB HEADLESS MODE ---
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import google.generativeai as genai
from datetime import datetime

# ==============================================================================
# 🔐 USER SETTINGS
# ==============================================================================
GEMINI_API_KEY = "AIzaSyAQhJmvE8VkImSSN-Aiv98nOv_1prfD7QY" 
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003534299054"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

# --- CONFIGURATION ---
START_HOUR = 7
END_HOUR = 21
MAX_DAILY_SIGNALS = 8
DATA_FILE = "bot_data.json"
RISK_PER_TRADE_ROI = 60 # Max Loss % allowed per trade

# Setup Gemini AI (Fixed Model Name)
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') # මම මෙතන නම හරියටම හැදුවා
except Exception as e:
    st.error(f"API Key Error: {e}")

st.set_page_config(page_title="Ghost Protocol AI Vision", page_icon="👁️", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- DATA MANAGEMENT ---
def load_data():
    default = {
        "bot_active": True, "daily_count": 0, "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], "history": [], "last_scan_block_id": -1,
        "sent_morning": False, "sent_goodbye": False, "scan_log": "", "force_scan": False,
        "coins": ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "LTC", "DOT", "MATIC", "UNI", "BCH", "FIL", "NEAR", "ATOM", "ICP", "IMX", "APT"]
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if data.get("last_reset_date") != datetime.now(lz).strftime("%Y-%m-%d"):
                    data.update({"daily_count": 0, "signaled_coins": [], "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"), "sent_morning": False, "sent_goodbye": False, "scan_log": ""})
                    with open(DATA_FILE, "w") as fw: json.dump(data, fw)
                return data
        except: return default
    return default

def save_full_state():
    # Helper to clean session state before saving
    serializable_data = {
        "bot_active": st.session_state.get("bot_active", True),
        "daily_count": st.session_state.get("daily_count", 0),
        "last_reset_date": st.session_state.get("last_reset_date", ""),
        "signaled_coins": st.session_state.get("signaled_coins", []),
        "history": st.session_state.get("history", []),
        "last_scan_block_id": st.session_state.get("last_scan_block_id", -1),
        "sent_morning": st.session_state.get("sent_morning", False),
        "sent_goodbye": st.session_state.get("sent_goodbye", False),
        "scan_log": st.session_state.get("scan_log", ""),
        "force_scan": st.session_state.get("force_scan", False),
        "coins": st.session_state.get("coins", [])
    }
    with open(DATA_FILE, "w") as f: json.dump(serializable_data, f)

# --- TELEGRAM ---
def send_telegram(msg, is_sticker=False, image_path=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        elif image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as img_file:
                files = {'photo': img_file}
                data = {'chat_id': CHANNEL_ID, 'caption': msg, 'parse_mode': 'HTML'}
                requests.post(url + "sendPhoto", files=files, data=data)
        else:
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- DATA FETCHING ---
def get_data(symbol):
    try:
        ticker = f"{symbol}-USD"
        df = yf.download(ticker, period="2d", interval="15m", progress=False) 
        if df.empty: return pd.DataFrame()

        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        cols_map = {}
        for col in df.columns:
            c = str(col).lower()
            if 'date' in c or 'time' in c: cols_map[col] = 'Date'
            elif 'open' in c: cols_map[col] = 'Open'
            elif 'high' in c: cols_map[col] = 'High'
            elif 'low' in c: cols_map[col] = 'Low'
            elif 'close' in c: cols_map[col] = 'Close'
            elif 'volume' in c: cols_map[col] = 'Volume'
            
        df = df.rename(columns=cols_map)
        
        if 'Date' in df.columns:
            df = df.set_index('Date')
        
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
                
        return df.dropna()
            
    except Exception as e:
        print(f"Data Error: {e}")
        return pd.DataFrame()

# --- CHART GENERATION ---
def generate_chart_image(df, coin_name):
    filename = f"chart_{coin_name}.png"
    if 'Close' not in df.columns or 'Open' not in df.columns: return None, f"Missing Columns"
    if len(df) < 5: return None, "Not enough data"

    try:
        mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', inherit=True)
        s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
        ema200 = df['Close'].ewm(span=200).mean()
        plot_df = df.tail(60)
        
        add_plots = []
        if len(plot_df) == len(ema200.tail(60)):
            add_plots = [mpf.make_addplot(ema200.tail(60), color='blue', width=1.5)]

        mpf.plot(plot_df, type='candle', style=s, volume=True, addplot=add_plots, savefig=filename, figsize=(10, 6))
        return filename, None
    except Exception as e:
        return None, str(e)

# --- AI ANALYSIS ---
def analyze_with_vision(df, coin_name):
    if df.empty or len(df) < 30: return "NEUTRAL", 0, 0, 0, 0, 0, "No Data", None
    chart_path, error_msg = generate_chart_image(df, coin_name)
    if not chart_path: return "NEUTRAL", 0, 0, 0, 0, 0, f"Chart Err: {error_msg}", None

    try:
        img = genai.upload_file(chart_path)
        prompt = """
        Elite Crypto Trader analysis: Malaysian SNR, ICT, Liquidity & Price Action.
        Output ONLY JSON: {"signal": "LONG", "score": 90, "reason": "MSS + FVG rejection"}
        """
        response = model.generate_content([prompt, img])
        result = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        sig = result.get("signal", "NEUTRAL")
        score = int(result.get("score", 0))
        reason = result.get("reason", "AI Analysis")
        os.remove(chart_path)
    except Exception as e:
        return "NEUTRAL", 0, 0, 0, 0, 0, f"AI Err: {str(e)[:20]}", chart_path

    # Leverage calc
    curr_close = df['Close'].iloc[-1]
    atr = (df['High'].iloc[-1] - df['Low'].iloc[-1])
    sl = curr_close - (atr * 2) if sig == "LONG" else curr_close + (atr * 2)
    sl_dist = abs(curr_close - sl) / curr_close * 100
    leverage = int(max(5, min(RISK_PER_TRADE_ROI / sl_dist, 75))) if sl_dist > 0 else 20

    return (sig if score > 85 else "NEUTRAL"), score, curr_close, leverage, sl, 0, reason, chart_path

# ==============================================================================
# MAIN UI
# ==============================================================================

# Init
saved_data = load_data()
for k, v in saved_data.items():
    if k not in st.session_state: st.session_state[k] = v

# --- SIDEBAR ---
st.sidebar.title("🎛️ Control Panel")
current_time = datetime.now(lz)
is_within_hours = START_HOUR <= current_time.hour < END_HOUR

status_color = "red"; status_text = "STOPPED 🔴"
if st.session_state.bot_active:
    if st.session_state.daily_count >= MAX_DAILY_SIGNALS: status_color = "orange"; status_text = "DAILY LIMIT 🛑"
    elif is_within_hours: status_color = "green"; status_text = "RUNNING 🟢"
    else: status_color = "orange"; status_text = "SLEEPING 💤"

st.sidebar.markdown(f"**Status:** :{status_color}[{status_text}]")
st.sidebar.metric("Daily Signals", f"{st.session_state.daily_count} / {MAX_DAILY_SIGNALS}")

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START", use_container_width=True): st.session_state.bot_active = True; save_full_state(); st.rerun()
if col2.button("⏹️ STOP", use_container_width=True): st.session_state.bot_active = False; save_full_state(); st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚡ FORCE SCAN NOW", use_container_width=True): st.session_state.force_scan = True; st.rerun()
if st.sidebar.button("🔄 RESET LIMIT (Admin)", use_container_width=True):
    st.session_state.daily_count = 0; st.session_state.signaled_coins = []; st.session_state.sent_goodbye = False; save_full_state(); st.rerun()

# Coin Manager
st.sidebar.markdown("---")
st.sidebar.subheader("🪙 Coin Manager")
new_coin = st.sidebar.text_input("Add Coin", "").upper()
if st.sidebar.button("➕ Add Coin"):
    if new_coin and new_coin not in st.session_state.coins:
        st.session_state.coins.append(new_coin); save_full_state(); st.rerun()

rem_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove"):
    if rem_coin in st.session_state.coins:
        st.session_state.coins.remove(rem_coin); save_full_state(); st.rerun()

# Test Button
st.sidebar.markdown("---")
if st.sidebar.button("📡 Test Telegram & Chart", use_container_width=True):
    test_df = get_data("BTC")
    if not test_df.empty:
        c_path, _ = generate_chart_image(test_df, "BTC")
        if c_path:
            send_telegram("", is_sticker=True)
            time.sleep(1)
            send_telegram("💎<b>GHOST TEST SUCCESS</b>💎\nSystem Ready.", image_path=c_path)
            st.sidebar.success("Sent!")

# --- MAIN ---
st.title("👻 GHOST PROTOCOL 5.0 : THE MASTERPIECE")
st.metric("🇱🇰 Sri Lanka Time", current_time.strftime("%H:%M:%S"))

tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

def run_scan():
    if st.session_state.daily_count >= MAX_DAILY_SIGNALS: return
    st.markdown(f"### 👁️ AI Scanning {len(st.session_state.coins)} Coins...")
    progress_bar = st.progress(0); status_area = st.empty()

    for i, coin in enumerate(st.session_state.coins):
        if coin in st.session_state.signaled_coins: continue
        status_area.markdown(f"📸 **Capturing:** `{coin}` ...")
        df = get_data(coin)
        if df.empty: continue 

        sig, score, price, leverage, sl, _, reason, chart_path = analyze_with_vision(df, coin)
        
        if sig != "NEUTRAL":
            send_telegram("", is_sticker=True); time.sleep(2)
            # TP calc
            risk = abs(price - sl)
            tps = [price + risk if sig == "LONG" else price - risk, price + 2*risk if sig == "LONG" else price - 2*risk, price + 3*risk if sig == "LONG" else price - 3*risk, price + 4*risk if sig == "LONG" else price - 4*risk]
            
            p_fmt = ".4f" if price < 50 else ".2f"
            msg = f"💎<b>CRYPTO CAMPUS VIP</b>💎\n\n🌟 <b>{coin} USDT</b>\n\n{'🟢<b>Long</b>' if sig == 'LONG' else '🔴<b>Short</b>'}\n\n🚀<b>Isolated</b>\n📈<b>Leverage {leverage}X</b>\n\n💥<b>Entry {price:{p_fmt}}</b>\n\n✅<b>Take Profit</b>\n\n1️⃣ {tps[0]:{p_fmt}}\n2️⃣ {tps[1]:{p_fmt}}\n3️⃣ {tps[2]:{p_fmt}}\n4️⃣ {tps[3]:{p_fmt}}\n\n⭕ <b>Stop Loss {sl:{p_fmt}}</b>\n\n📝 <b>RR 1:4.0</b>\n\n⚠️ <b>Margin Use 1%-5%</b>"
            send_telegram(msg, image_path=chart_path)
            st.session_state.history.insert(0, {"Time": datetime.now(lz).strftime("%H:%M"), "Coin": coin, "Signal": sig})
            st.session_state.daily_count += 1; st.session_state.signaled_coins.append(coin); save_full_state()
            if st.session_state.daily_count >= MAX_DAILY_SIGNALS: break
        
        time.sleep(3); progress_bar.progress((i + 1) / len(st.session_state.coins))
    st.rerun()

with tab1:
    if st.session_state.bot_active:
        if is_within_hours:
            curr_block = current_time.hour * 4 + (current_time.minute // 15)
            if (curr_block != st.session_state.last_scan_block_id) or st.session_state.force_scan:
                st.session_state.last_scan_block_id = curr_block; st.session_state.force_scan = False; save_full_state(); run_scan()
            else: st.info("⏳ AI is watching... Next scan in 15 mins."); time.sleep(10); st.rerun()
        else: st.warning("💤 AI Sleeping..."); time.sleep(10); st.rerun()
    else: st.error("⚠️ AI STOPPED")

with tab2:
    if st.session_state.history: st.table(pd.DataFrame(st.session_state.history))
    else: st.info("No signals yet.")
