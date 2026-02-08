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
matplotlib.use('Agg') # Server එකේ චාට් අඳින්න මේක අනිවාර්යයි
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
        "bot_active": True, 
        "daily_count": 0, 
        "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], 
        "history": [], 
        "last_scan_block_id": -1,
        "sent_morning": False, 
        "sent_goodbye": False,
        "scan_log": "",
        "force_scan": False
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
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
                return data
        except: return default
    return default

def save_full_state():
    data = {
        "bot_active": st.session_state.bot_active, 
        "daily_count": st.session_state.daily_count,
        "last_reset_date": st.session_state.last_reset_date, 
        "signaled_coins": st.session_state.signaled_coins,
        "history": st.session_state.history, 
        "last_scan_block_id": st.session_state.last_scan_block_id,
        "sent_morning": st.session_state.sent_morning, 
        "sent_goodbye": st.session_state.sent_goodbye,
        "scan_log": st.session_state.scan_log,
        "force_scan": st.session_state.force_scan
    }
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- TELEGRAM FUNCTION (UPDATED FOR PHOTOS) ---
def send_telegram(msg, is_sticker=False, image_path=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        elif image_path and os.path.exists(image_path):
            # Send Photo with Caption
            with open(image_path, 'rb') as img_file:
                files = {'photo': img_file}
                data = {'chat_id': CHANNEL_ID, 'caption': msg, 'parse_mode': 'HTML'}
                requests.post(url + "sendPhoto", files=files, data=data)
        else:
            # Text Only
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- DATA FETCHING ---
def get_data(symbol):
    try:
        ticker = f"{symbol}-USD"
        df = yf.download(ticker, period="2d", interval="15m", progress=False) 
        if not df.empty:
            df = df.reset_index()
            if isinstance(df.columns, pd.MultiIndex): 
                try: df.columns = df.columns.droplevel(1)
                except: pass
            
            required_cols = {'Datetime': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'}
            df = df.rename(columns=required_cols)
            if 'Date' in df.columns: df = df.set_index('Date')
            return df
    except: return pd.DataFrame()
    return pd.DataFrame()

# --- CHART GENERATION (HELPER) ---
def generate_chart_image(df, coin_name):
    filename = f"chart_{coin_name}.png"
    mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', inherit=True)
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
    
    ema200 = df['Close'].ewm(span=200).mean()
    add_plots = [mpf.make_addplot(ema200[-60:], color='blue', width=1.5)] if len(df) > 200 else []

    try:
        mpf.plot(
            df.tail(60),
            type='candle',
            style=s,
            volume=True,
            addplot=add_plots,
            title=f"{coin_name} - 15m (AI Vision)",
            savefig=filename,
            figsize=(10, 6),
            off_image=True
        )
        return filename
    except:
        return None

# ==============================================================================
# 👁️ CORE: AI VISION ANALYSIS
# ==============================================================================

def analyze_with_vision(df, coin_name):
    if df.empty or len(df) < 30: return "NEUTRAL", 0, 0, 0, 0, 0, "No Data", None

    # 1. Generate Chart
    chart_path = generate_chart_image(df, coin_name)
    if not chart_path: return "NEUTRAL", 0, 0, 0, 0, 0, "Chart Error", None

    # 2. Ask Gemini AI
    try:
        img = genai.upload_file(chart_path)
        
        prompt = """
        You are a professional crypto day trader. Analyze this 15-minute chart image.
        
        Key Rules:
        1. Identify the immediate trend (based on the candles shown).
        2. Look for CLEAR setups (Breakouts, Rejections, Supply/Demand).
        3. Blue line is EMA 200.
        
        Output ONLY a JSON string:
        {"signal": "LONG", "score": 90, "reason": "Reason in 10 words"}
        
        Possible signals: "LONG", "SHORT", "NEUTRAL".
        Score: 0-100 (Threshold 85).
        """
        
        response = model.generate_content([prompt, img])
        result_text = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(result_text)
        
        sig = result.get("signal", "NEUTRAL")
        score = int(result.get("score", 0))
        reason = result.get("reason", "AI Analysis")

    except Exception as e:
        return "NEUTRAL", 0, 0, 0, 0, 0, f"AI Err: {str(e)[:20]}", chart_path

    # 3. Calculate Levels
    curr_close = df['Close'].iloc[-1]
    atr = (df['High'].iloc[-1] - df['Low'].iloc[-1])
    sl_long = curr_close - (atr * 2)
    sl_short = curr_close + (atr * 2)

    if score < 85: sig = "NEUTRAL"

    # Important: Return chart_path so we can send it to Telegram
    return sig, score, curr_close, atr, sl_long, sl_short, reason, chart_path

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

st.sidebar.title("🎛️ Control Panel")

# --- TEST BUTTON LOGIC ---
if st.sidebar.button("📡 Test Telegram with Chart"):
    st.sidebar.info("Generating BTC Chart for Test...")
    test_df = get_data("BTC")
    if not test_df.empty:
        test_chart = generate_chart_image(test_df, "BTC")
        if test_chart:
            test_msg = "💎<b>GHOST PROTOCOL TEST</b>💎\n\n📸 This is how the chart will look with the signal!\n\n🚀 <b>System is Online</b>"
            send_telegram(test_msg, image_path=test_chart)
            st.sidebar.success("Test Sent with Chart! 📸")
            os.remove(test_chart) # Clean up
        else:
            st.sidebar.error("Failed to generate test chart")
    else:
        st.sidebar.error("Failed to fetch BTC data")

st.sidebar.markdown("---")
coins_list = st.session_state.coins
current_time = datetime.now(lz)
is_within_hours = START_HOUR <= current_time.hour < END_HOUR

status_color = "red"; status_text = "STOPPED 🔴"
if st.session_state.bot_active:
    if st.session_state.daily_count >= MAX_DAILY_SIGNALS:
        status_color = "orange"; status_text = "DAILY LIMIT REACHED 🛑"
    elif is_within_hours:
        status_color = "green"; status_text = "RUNNING 🟢"
    else:
        status_color = "orange"; status_text = "SLEEPING 💤"

st.sidebar.markdown(f"### Status: **:{status_color}[{status_text}]**")
st.sidebar.caption("Mode: 👁️ AI VISION (Gemini Pro)")

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START"): st.session_state.bot_active = True; save_full_state(); st.rerun()
if col2.button("⏹️ STOP"): st.session_state.bot_active = False; save_full_state(); st.rerun()

if st.sidebar.button("⚡ FORCE SCAN NOW"): st.session_state.force_scan = True; st.rerun()
if st.sidebar.button("🔄 RESET LIMIT"): st.session_state.daily_count = 0; st.session_state.signaled_coins = []; save_full_state(); st.rerun()

st.title("👻 GHOST PROTOCOL 3.2 : AI VISION + CHARTS")
st.write("Engine: **Google Gemini 1.5 Pro** | Feature: **Chart Image in Telegram** 📸")

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
            status_area.markdown(f"📸 **Capturing Chart:** `{coin}` ...")
            
            df = get_data(coin)
            if df.empty: continue 

            # CALL AI FUNCTION (Now returns chart_path too)
            sig, score, price, atr, sl_long, sl_short, reason, chart_path = analyze_with_vision(df, coin)
            
            if score >= 85: score_color = "green"
            elif score <= 15: score_color = "red"
            else: score_color = "orange"
            
            status_area.markdown(f"🤖 **AI Analyzing:** `{coin}` | 🧠 **Verdict:** :{score_color}[{sig} ({score}%)]")
            
            log_entry = f"`{coin}`: {sig} ({score}%) - {reason} | "
            st.session_state.scan_log = log_entry + st.session_state.scan_log
            if len(st.session_state.scan_log) > 1000: st.session_state.scan_log = st.session_state.scan_log[:1000]

            if sig != "NEUTRAL":
                if st.session_state.daily_count < MAX_DAILY_SIGNALS:
                    send_telegram("", is_sticker=True); time.sleep(3)
                    
                    if sig == "LONG":
                        sl = sl_long 
                        tp_dist = (price - sl) * 2
                        tps = [price + (tp_dist * 0.6 * x) for x in range(1, 5)]
                        emoji = "🟢"; side = "Long"
                    else:
                        sl = sl_short
                        tp_dist = (sl - price) * 2
                        tps = [price - (tp_dist * 0.6 * x) for x in range(1, 5)]
                        emoji = "🔴"; side = "Short"

                    p_fmt = ".4f" if price < 50 else ".2f"
                    
                    msg = (
                        f"💎<b>CRYPTO CAMPUS AI VISION</b>💎\n\n"
                        f"👁️ <b>{coin} USDT</b>\n\n"
                        f"{emoji} <b>{side} Signal</b>\n"
                        f"🧠 <b>Reason:</b> {reason}\n\n"
                        f"💥<b>Entry {price:{p_fmt}}</b>\n\n"
                        f"✅<b>Targets:</b>\n"
                        f"1️⃣ {tps[0]:{p_fmt}}\n"
                        f"2️⃣ {tps[1]:{p_fmt}}\n"
                        f"3️⃣ {tps[2]:{p_fmt}}\n\n"
                        f"⭕ <b>Stop Loss {sl:{p_fmt}}</b>\n\n"
                        f"⚠️ <b>Risk: 1-2% Only (AI Test)</b>"
                    )
                    
                    # Send with CHART IMAGE!
                    send_telegram(msg, image_path=chart_path)
                    
                    st.session_state.history.insert(0, {"Time": current_time.strftime("%H:%M"), "Coin": coin, "Signal": sig, "Reason": reason})
                    st.session_state.daily_count += 1
                    st.session_state.signaled_coins.append(coin)
                    save_full_state()
                    
                    if st.session_state.daily_count >= MAX_DAILY_SIGNALS: break
            
            # Clean up the chart file if it exists and wasn't sent (or even if sent)
            # Actually, inside the loop, we should clean up after sending
            if chart_path and os.path.exists(chart_path):
                os.remove(chart_path)

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
        else:
            st.warning("💤 AI Sleeping..."); time.sleep(10); st.rerun()
    else: st.error("⚠️ AI STOPPED"); time.sleep(2)

with tab2:
    if st.session_state.history: st.table(pd.DataFrame(st.session_state.history))
    else: st.info("No AI signals yet.")
