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

# Setup Gemini AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"API Key Error: {e}")

st.set_page_config(page_title="Ghost Protocol AI Vision", page_icon="👁️", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- DATA MANAGEMENT ---
def load_data():
    default = {
        "bot_active": True, "daily_count": 0, "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], "history": [], "last_scan_block_id": -1,
        "sent_morning": False, "sent_goodbye": False, "scan_log": "", "force_scan": False
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
    data = st.session_state.to_dict()
    serializable_data = {k: v for k, v in data.items() if k in ["bot_active", "daily_count", "last_reset_date", "signaled_coins", "history", "last_scan_block_id", "sent_morning", "sent_goodbye", "scan_log", "force_scan", "coins"]}
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
    
    if 'Close' not in df.columns or 'Open' not in df.columns:
        return None, f"Missing Columns"
    if len(df) < 5:
        return None, "Not enough data"

    try:
        mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', inherit=True)
        s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
        
        # We plot EMA 200 just for AI context, but logic is Pure Price Action
        ema200 = df['Close'].ewm(span=200).mean()
        plot_df = df.tail(60)
        
        add_plots = []
        if len(plot_df) == len(ema200.tail(60)):
            add_plots = [mpf.make_addplot(ema200.tail(60), color='blue', width=1.5)]

        mpf.plot(
            plot_df,
            type='candle',
            style=s,
            volume=True,
            addplot=add_plots,
            title=f"{coin_name} - 15m (Ghost Protocol V5)",
            savefig=filename,
            figsize=(10, 6)
        )
        return filename, None
    except Exception as e:
        return None, str(e)

# ==============================================================================
# 👁️ CORE: AI VISION ANALYSIS (UPDATED PROMPT)
# ==============================================================================

def analyze_with_vision(df, coin_name):
    if df.empty or len(df) < 30: return "NEUTRAL", 0, 0, 0, 0, 0, "No Data", None

    chart_path, error_msg = generate_chart_image(df, coin_name)
    
    if not chart_path: 
        return "NEUTRAL", 0, 0, 0, 0, 0, f"Chart Err: {error_msg}", None

    try:
        img = genai.upload_file(chart_path)
        
        # --- THE MASTER PROMPT ---
        prompt = """
        You are an elite Crypto Trader specializing in Malaysian SNR, ICT (Smart Money Concepts), Liquidity, and Price Action.
        Analyze this 15-minute chart image deeply.
        
        CHECKLIST FOR ENTRY:
        1. **Liquidity (The Fuel):** Look for Liquidity Sweeps (Raids) of previous Highs/Lows (BSL/SSL). Did a wick grab liquidity and reverse?
        2. **Market Structure (The Map):** Look for MSS (Market Structure Shift) or CHoCH (Change of Character) with displacement.
        3. **Malaysian SNR (The Level):** Look for QML (Quasimodo), RBS, SBR, or MPL (Maximum Pain Level) setups.
        4. **ICT Arrays (The Trigger):** Identify Order Blocks (OB) or FVG (Fair Value Gaps) that are being respected.
        5. **Price Action:** Look for Pinbars, Engulfing candles, or Rejection wicks at key levels.
        
        STRICT RULES:
        - IGNORE Indicators (RSI/MACD). Focus ONLY on Candles and Structure.
        - If the market is chopping (Ranging) inside a narrow zone, signal NEUTRAL.
        - Only signal if you see a CLEAR setup from the checklist above.
        
        Output ONLY a JSON string:
        {"signal": "LONG", "score": 90, "reason": "Liquidity Sweep of Low + MSS + Rejection from Bullish OB", "sl_location": "Just below the swing low"}
        
        Possible signals: "LONG", "SHORT", "NEUTRAL".
        Score: 0-100 (Must be > 85 for a signal).
        Reason: Use professional terms (e.g., "Liquidity Grab", "Mitigation", "QML"). Max 10 words.
        """
        
        response = model.generate_content([prompt, img])
        result_text = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(result_text)
        
        sig = result.get("signal", "NEUTRAL")
        score = int(result.get("score", 0))
        reason = result.get("reason", "AI Analysis")
        
        try: os.remove(chart_path)
        except: pass

    except Exception as e:
        return "NEUTRAL", 0, 0, 0, 0, 0, f"AI Err: {str(e)[:20]}", chart_path

    # --- DYNAMIC LEVERAGE CALCULATION ---
    curr_close = df['Close'].iloc[-1]
    
    # Calculate SL based on Swing Low/High (Simplified logic using ATR for safety fallback)
    atr = (df['High'].iloc[-1] - df['Low'].iloc[-1])
    
    if sig == "LONG":
        # Logical SL: Below recent structure (using ATR as buffer)
        sl_price = curr_close - (atr * 2) 
        # Calculate Distance %
        sl_dist_percent = abs(curr_close - sl_price) / curr_close * 100
    elif sig == "SHORT":
        # Logical SL: Above recent structure
        sl_price = curr_close + (atr * 2)
        sl_dist_percent = abs(sl_price - curr_close) / curr_close * 100
    else:
        sl_price = 0
        sl_dist_percent = 1 # Dummy

    # --- MAGIC FORMULA: Leverage = 60 / SL Distance % ---
    if sl_dist_percent > 0:
        raw_leverage = RISK_PER_TRADE_ROI / sl_dist_percent
        # Cap leverage between 5x and 75x for safety
        leverage = int(max(5, min(raw_leverage, 75)))
    else:
        leverage = 20 # Default fallback

    return sig, score, curr_close, leverage, sl_price, 0, reason, chart_path

# ==============================================================================
# MAIN APP LOOP
# ==============================================================================

saved_data = load_data()
for k, v in saved_data.items():
    if k not in st.session_state: st.session_state[k] = v

if 'scan_log' not in st.session_state: st.session_state.scan_log = ""
if 'force_scan' not in st.session_state: st.session_state.force_scan = False
if 'coins' not in st.session_state:
    st.session_state.coins = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "LTC", "DOT", "MATIC", "UNI", "BCH", "FIL", "NEAR", "ATOM", "ICP", "IMX", "APT"]

# --- SIDEBAR ---
st.sidebar.title("🎛️ Control Panel")
current_time = datetime.now(lz)
is_within_hours = START_HOUR <= current_time.hour < END_HOUR

# Status
status_color = "red"; status_text = "STOPPED 🔴"
if st.session_state.bot_active:
    if st.session_state.daily_count >= MAX_DAILY_SIGNALS:
        status_color = "orange"; status_text = "DAILY LIMIT 🛑"
    elif is_within_hours:
        status_color = "green"; status_text = "RUNNING 🟢"
    else:
        status_color = "orange"; status_text = "SLEEPING 💤"

st.sidebar.markdown(f"**Status:** :{status_color}[{status_text}]")
st.sidebar.caption(f"Time: {START_HOUR}:00 - {END_HOUR}:00")
st.sidebar.metric("Daily Signals", f"{st.session_state.daily_count} / {MAX_DAILY_SIGNALS}")
st.sidebar.caption("Leverage: Dynamic (Risk Based)")

if st.session_state.signaled_coins:
    st.sidebar.caption(f"Today: {', '.join(st.session_state.signaled_coins)}")

# Controls
col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START", use_container_width=True): st.session_state.bot_active = True; save_full_state(); st.rerun()
if col2.button("⏹️ STOP", use_container_width=True): st.session_state.bot_active = False; save_full_state(); st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚡ FORCE SCAN NOW", use_container_width=True): st.session_state.force_scan = True; st.rerun()

if st.sidebar.button("🔄 RESET LIMIT (Admin)", use_container_width=True):
    st.session_state.daily_count = 0
    st.session_state.signaled_coins = []
    st.session_state.sent_goodbye = False
    save_full_state()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🪙 Coin Manager")
new_coin = st.sidebar.text_input("Add Coin (e.g. SUI)", "").upper()
if st.sidebar.button("➕ Add Coin"):
    if new_coin and new_coin not in st.session_state.coins:
        st.session_state.coins.append(new_coin); save_full_state(); st.success(f"{new_coin} Added!")

remove_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove Selected"):
    if remove_coin in st.session_state.coins:
        st.session_state.coins.remove(remove_coin); save_full_state(); st.rerun()

st.sidebar.markdown("---")

# --- FORMATTING FUNCTION ---
def format_vip_message(coin, sig, price, sl, tps, leverage):
    p_fmt = ".4f" if price < 50 else ".2f"
    
    roi_1 = round(abs(tps[0]-price)/price*100*leverage, 1)
    roi_2 = round(abs(tps[1]-price)/price*100*leverage, 1)
    roi_3 = round(abs(tps[2]-price)/price*100*leverage, 1)
    roi_4 = round(abs(tps[3]-price)/price*100*leverage, 1)
    
    sl_roi = round(abs(price-sl)/price*100*leverage, 1)
    
    risk = abs(price - sl)
    reward = abs(tps[3] - price)
    rr = round(reward / risk, 1) if risk > 0 else 0
    
    if sig == "LONG":
        direction_icon = "🟢"
        direction_text = "Long"
    else:
        direction_icon = "🔴"
        direction_text = "Short"

    msg = (
        f"💎<b>CRYPTO CAMPUS VIP</b>💎\n\n"
        f"🌟 <b>{coin} USDT</b>\n\n"
        f"{direction_icon}<b>{direction_text}</b>\n\n"
        f"🚀<b>Isolated</b>\n"
        f"📈<b>Leverage {leverage}X</b>\n\n"
        f"💥<b>Entry {price:{p_fmt}}</b>\n\n"
        f"✅<b>Take Profit</b>\n\n"
        f"1️⃣ {tps[0]:{p_fmt}} ({roi_1}%)\n"
        f"2️⃣ {tps[1]:{p_fmt}} ({roi_2}%)\n"
        f"3️⃣ {tps[2]:{p_fmt}} ({roi_3}%)\n"
        f"4️⃣ {tps[3]:{p_fmt}} ({roi_4}%)\n\n"
        f"⭕ <b>Stop Loss {sl:{p_fmt}} ({sl_roi}%)</b>\n\n"
        f"📝 <b>RR 1:{rr}</b>\n\n"
        f"⚠️ <b>Margin Use 1%-5%(Trading Plan Use)</b>"
    )
    return msg

# --- TEST BUTTON ---
if st.sidebar.button("📡 Test Telegram & Chart", use_container_width=True):
    st.sidebar.info("Generating BTC Chart...")
    test_df = get_data("BTC")
    if not test_df.empty:
        c_path, c_err = generate_chart_image(test_df, "BTC")
        if c_path:
            # 1. Send Sticker
            send_telegram("", is_sticker=True)
            time.sleep(1)
            
            # 2. Generate Real-Like Test Data
            price = test_df['Close'].iloc[-1]
            # Simulate a 1% SL distance for test
            sl = price * 0.99 
            sl_dist = 1.0
            lev = int(60 / sl_dist) # Logic Test: 60x leverage
            
            tps = [price*1.005, price*1.01, price*1.015, price*1.02]
            
            msg = format_vip_message("BTC", "LONG", price, sl, tps, leverage=lev)
            
            # 3. Send
            send_telegram(msg, image_path=c_path)
            st.sidebar.success(f"Test Signal Sent! (Lev: {lev}x)")
        else:
            st.sidebar.error(f"Failed: {c_err}")
    else:
        st.sidebar.error("Failed to fetch BTC")

# --- MAIN CONTENT ---
st.title("👻 GHOST PROTOCOL 5.0 : THE MASTERPIECE")
st.write("Engine: **Gemini 1.5 Pro** | Concepts: **Malaysian SNR, ICT, Liquidity**")
st.metric("🇱🇰 Sri Lanka Time", current_time.strftime("%H:%M:%S"))

coins_list = st.session_state.coins
tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

def run_scan():
    if st.session_state.daily_count >= MAX_DAILY_SIGNALS: return

    st.markdown(f"### 👁️ AI Scanning {len(coins_list)} Coins...")
    progress_bar = st.progress(0); status_area = st.empty()
    if 'scan_log' not in st.session_state: st.session_state.scan_log = ""

    for i, coin in enumerate(coins_list):
        if coin in st.session_state.signaled_coins:
            progress_bar.progress((i + 1) / len(coins_list)); continue

        try:
            status_area.markdown(f"📸 **Capturing:** `{coin}` ...")
            df = get_data(coin)
            if df.empty: continue 

            # AI Analysis + Dynamic Leverage Calculation
            sig, score, price, leverage, sl, _, reason, chart_path = analyze_with_vision(df, coin)
            
            if score >= 85: score_color = "green"
            elif score <= 15: score_color = "red"
            else: score_color = "orange"
            
            status_area.markdown(f"🤖 **AI Analyzing:** `{coin}` | 🧠 **Verdict:** :{score_color}[{sig} ({score}%)]")
            
            log_entry = f"`{coin}`: {sig} ({score}%) - {reason} | "
            st.session_state.scan_log = log_entry + st.session_state.scan_log
            if len(st.session_state.scan_log) > 1000: st.session_state.scan_log = st.session_state.scan_log[:1000]

            if sig != "NEUTRAL":
                if st.session_state.daily_count < MAX_DAILY_SIGNALS:
                    send_telegram("", is_sticker=True); time.sleep(2)
                    
                    # Calculate TPs based on Risk:Reward
                    risk_dist = abs(price - sl)
                    if sig == "LONG":
                        tps = [
                            price + (risk_dist * 1), # 1:1
                            price + (risk_dist * 2), # 1:2
                            price + (risk_dist * 3), # 1:3
                            price + (risk_dist * 4)  # 1:4
                        ]
                    else:
                        tps = [
                            price - (risk_dist * 1),
                            price - (risk_dist * 2),
                            price - (risk_dist * 3),
                            price - (risk_dist * 4)
                        ]
                    
                    msg = format_vip_message(coin, sig, price, sl, tps, leverage)
                    send_telegram(msg, image_path=chart_path)
                    
                    st.session_state.history.insert(0, {"Time": current_time.strftime("%H:%M"), "Coin": coin, "Signal": sig, "Reason": reason})
                    st.session_state.daily_count += 1
                    st.session_state.signaled_coins.append(coin)
                    save_full_state()
                    if st.session_state.daily_count >= MAX_DAILY_SIGNALS: break
            
            if chart_path and os.path.exists(chart_path): os.remove(chart_path)

        except Exception as e:
            print(f"Error {coin}: {e}")
            time.sleep(1)
        
        time.sleep(4) 
        progress_bar.progress((i + 1) / len(coins_list))
    
    status_area.empty(); st.success("AI Scan Complete!"); return

with tab1:
    if st.session_state.scan_log: st.markdown(f"#### 📝 AI Thoughts:\n{st.session_state.scan_log}")
    if st.session_state.bot_active:
        if is_within_hours:
            current_block_id = current_time.hour * 4 + (current_time.minute // 15)
            if (current_block_id != st.session_state.last_scan_block_id) or st.session_state.force_scan:
                st.session_state.last_scan_block_id = current_block_id
                st.session_state.force_scan = False
                save_full_state()
                run_scan()
                st.rerun()
            else:
                st.info("⏳ AI is watching the markets... (Next scan in 15 mins)")
                time.sleep(10); st.rerun()
        else: st.warning("💤 AI Sleeping..."); time.sleep(10); st.rerun()
    else: st.error("⚠️ AI STOPPED"); time.sleep(2)

with tab2:
    if st.session_state.history: st.table(pd.DataFrame(st.session_state.history))
    else: st.info("No AI signals yet.")
