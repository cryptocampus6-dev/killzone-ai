import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf # Vision සදහා Chart අඳින්න ඕනේ
import base64
from datetime import datetime
import re

# ==============================================================================
# 🔐 USER SETTINGS (GEMINI DIRECT API)
# ==============================================================================
# ඔයා කලින් දුන්න Gemini Key එක (මේක වැඩ නැත්නම් අලුත් එකක් දාගන්න)
GEMINI_API_KEY = "AIzaSyAamFhulobiwypsDB7HMS8Qxh1j6dfYnUQ" 

TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003534299054"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

START_HOUR = 7   
END_HOUR = 21    
MAX_DAILY_SIGNALS = 8
DATA_FILE = "bot_data.json"

st.set_page_config(page_title="GHOST VISION X 🚀", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- DATA MANAGEMENT ---
def load_data():
    default_coins = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "LTC"]
    default = {
        "bot_active": False, "daily_count": 0, "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], "history": [], "coins": default_coins,
        "sent_morning": False, "sent_goodbye": False, "force_scan": False
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                for key, val in default.items():
                    if key not in data: data[key] = val
                return data
        except: return default
    return default

def save_full_state():
    serializable_data = {k: v for k, v in st.session_state.items() 
                        if k in ["bot_active", "daily_count", "last_reset_date", 
                                 "signaled_coins", "history", "coins", 
                                 "sent_morning", "sent_goodbye", "force_scan"]}
    with open(DATA_FILE, "w") as f: json.dump(serializable_data, f)

# --- TELEGRAM ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker: requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else: requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

# --- VIP MESSAGE FORMATTER ---
def format_vip_message(coin, sig, price, sl, tps, leverage, reason):
    p_fmt = ".4f" if price < 50 else ".2f"
    roi_1 = round(abs(tps[0]-price)/price*100*leverage, 1)
    sl_roi = round(abs(price-sl)/price*100*leverage, 1)
    risk = abs(price - sl); reward = abs(tps[3] - price)
    rr = round(reward / risk, 1) if risk > 0 else 0
    direction_text = "🟢Long" if sig == "LONG" else "🔴Short"

    msg = (
        f"💎<b>CRYPTO CAMPUS VIP (AI VISION)</b>💎\n\n"
        f"🌟 <b>{coin} USDT</b>\n\n"
        f"{direction_text}\n"
        f"🚀<b>Isolated</b> | 📈<b>Leverage {leverage}X</b>\n\n"
        f"💥<b>Entry {price:{p_fmt}}</b>\n\n"
        f"✅<b>Take Profit</b>\n"
        f"1️⃣ {tps[0]:{p_fmt}} ({roi_1}%)\n"
        f"2️⃣ {tps[1]:{p_fmt}}\n"
        f"3️⃣ {tps[2]:{p_fmt}}\n"
        f"4️⃣ {tps[3]:{p_fmt}}\n\n"
        f"⭕ <b>Stop Loss {sl:{p_fmt}} ({sl_roi}%)</b>\n\n"
        f"📝 <b>Reason: {reason}</b>\n"
        f"⚖️ <b>RR 1:{rr}</b>"
    )
    return msg

# --- DATA FETCHING ---
def get_data(symbol):
    try:
        ticker = f"{symbol}-USD"
        df = yf.download(ticker, period="5d", interval="15m", progress=False) 
        if df.empty: return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df.columns = [str(c) for c in df.columns]
        if 'Datetime' in df.columns: df = df.rename(columns={'Datetime': 'Date'})
        if 'Date' in df.columns: df = df.set_index('Date')
        
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for c in cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except: return pd.DataFrame()

# ==============================================================================
# 👁️ GEMINI DIRECT API VISION (The New Robust Eye)
# ==============================================================================
def generate_chart_image(df, coin_name):
    filename = f"temp_chart_{coin_name}.png"
    try:
        if len(df) < 50: return None
        mc = mpf.make_marketcolors(up='#00FF00', down='#FF0000', inherit=True)
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
        # Chart එක අඳිනවා
        mpf.plot(df.tail(60), type='candle', style=s, volume=False, savefig=filename, figsize=(10, 6))
        return filename
    except: return None

def analyze_with_gemini_vision(df, coin_name):
    # 1. Chart එක හදනවා
    chart_path = generate_chart_image(df, coin_name)
    if not chart_path: return "NEUTRAL", 0, 0, 0, [], 0, "Chart Gen Error"

    try:
        # 2. Image එක Base64 වලට හරවනවා
        with open(chart_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        # 3. DIRECT API REQUEST (No Library)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        
        prompt = """
        Analyze this crypto chart for a Scalping Trade (15m timeframe).
        Identify Trends, Liquidity Sweeps, and Order Blocks.
        Output MUST be strict JSON: {"signal": "LONG", "score": 90, "reason": "Bullish structure break"}
        OR {"signal": "SHORT", "score": 85, "reason": "Liquidity sweep at highs"}
        OR {"signal": "NEUTRAL", "score": 0, "reason": "Consolidation"}
        """
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {
                        "mime_type": "image/png",
                        "data": image_data
                    }}
                ]
            }]
        }
        
        # 4. Google එකට යවනවා
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        # File එක මකනවා (Clean up)
        if os.path.exists(chart_path): os.remove(chart_path)

        if response.status_code == 200:
            result = response.json()
            text_response = result['candidates'][0]['content']['parts'][0]['text']
            
            # JSON Clean up
            match = re.search(r'\{.*\}', text_response, re.DOTALL)
            if match:
                data = json.loads(match.group().replace("'", '"'))
                sig = data.get("signal", "NEUTRAL")
                score = int(data.get("score", 0))
                reason = data.get("reason", "AI Vision Scan")
            else:
                return "NEUTRAL", 0, 0, 0, [], 0, "AI Parse Error"
        else:
            return "NEUTRAL", 0, 0, 0, [], 0, f"API Error {response.status_code}"

    except Exception as e:
        if os.path.exists(chart_path): os.remove(chart_path)
        return "NEUTRAL", 0, 0, 0, [], 0, f"Connect Error"

    # 5. Technical Levels Calculation (Logic)
    curr_price = df['Close'].iloc[-1]
    atr = (df['High'].iloc[-1] - df['Low'].iloc[-1])
    risk = atr * 2
    
    sl = 0; tps = []
    
    if sig == "LONG":
        sl = curr_price - risk
        tps = [curr_price+(risk*1.5), curr_price+(risk*3), curr_price+(risk*5), curr_price+(risk*8)]
    elif sig == "SHORT":
        sl = curr_price + risk
        tps = [curr_price-(risk*1.5), curr_price-(risk*3), curr_price-(risk*5), curr_price-(risk*8)]

    return sig, score, curr_price, sl, tps, 20, reason

# ==============================================================================
# MAIN UI
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

st.sidebar.subheader("Coin Manager")
new_c = st.sidebar.text_input("Add Coin").upper()
if st.sidebar.button("Add"):
    if new_c and new_c not in st.session_state.coins: st.session_state.coins.append(new_c); save_full_state(); st.rerun()
rem_c = st.sidebar.selectbox("Remove", st.session_state.coins)
if st.sidebar.button("Delete"):
    if rem_c in st.session_state.coins: st.session_state.coins.remove(rem_c); save_full_state(); st.rerun()

# --- TELEGRAM TEST ---
st.sidebar.markdown("---")
if st.sidebar.button("🚀 Test Telegram", use_container_width=True):
    with st.sidebar.status("Sending..."):
        test_msg = format_vip_message("BTC", "LONG", 95000, 94000, [96000,97000,98000,100000], 20, "Test Signal")
        send_telegram(test_msg)
        send_telegram("", is_sticker=True)
    st.sidebar.success("Message Sent!")

# --- MAIN DASHBOARD ---
st.title("👻 GHOST VISION X 🚀")
st.markdown(f"LK Sri Lanka Time: **{datetime.now(lz).strftime('%H:%M:%S')}**")

tab1, tab2 = st.tabs(["📊 Vision Scanner", "📜 Signal History"])

with tab1:
    if st.session_state.bot_active:
        st.markdown("### 👁️ AI Scanning with Gemini Vision...")
        progress_bar = st.progress(0)
        status_area = st.empty()
        
        for i, coin in enumerate(st.session_state.coins):
            if not st.session_state.bot_active: break
            if coin in st.session_state.signaled_coins: continue
            
            status_area.markdown(f"📸 **Capturing:** `{coin}` Chart...")
            df = get_data(coin)
            if df.empty: continue
            
            # --- AI CALL ---
            sig, score, price, sl, tps, lev, reason = analyze_with_gemini_vision(df, coin)
            
            status_area.markdown(f"👀 **Checked:** {coin} | Signal: {sig} ({score}%) | 📝 {reason}")
            
            if sig != "NEUTRAL" and score >= 85:
                send_telegram("", is_sticker=True)
                msg = format_vip_message(coin, sig, price, sl, tps, lev, reason)
                send_telegram(msg)
                
                st.session_state.history.insert(0, {"Time": datetime.now(lz).strftime("%H:%M"), "Coin": coin, "Signal": sig})
                st.session_state.daily_count += 1
                st.session_state.signaled_coins.append(coin)
                save_full_state()
                st.rerun()
            
            progress_bar.progress((i + 1) / len(st.session_state.coins))
            time.sleep(1) # API Limit නොවදින්න පොඩි Break එකක්
    else:
        st.info("⚠️ Bot is Stopped. Click START to begin.")

with tab2:
    st.table(pd.DataFrame(st.session_state.history))
