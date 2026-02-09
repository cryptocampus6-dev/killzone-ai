import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import yfinance as yf

# --- MATPLOTLIB FOR INTERNAL AI VISION ONLY ---
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
START_HOUR = 7   # 07:00 AM
END_HOUR = 21    # 09:00 PM
MAX_DAILY_SIGNALS = 8
DATA_FILE = "bot_data.json"
RISK_PER_TRADE_ROI = 60 

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
    # --- 120 COINS LIST ---
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
                if data.get("last_reset_date") != datetime.now(lz).strftime("%Y-%m-%d"):
                    data.update({"daily_count": 0, "signaled_coins": [], "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"), "sent_morning": False, "sent_goodbye": False, "scan_log": ""})
                    with open(DATA_FILE, "w") as fw: json.dump(data, fw)
                
                if len(data.get("coins", [])) < 50:
                    data["coins"] = default_coins
                    with open(DATA_FILE, "w") as fw: json.dump(data, fw)
                return data
        except: return default
    return default

def save_full_state():
    serializable_data = {k: v for k, v in st.session_state.items() if k in ["bot_active", "daily_count", "last_reset_date", "signaled_coins", "history", "last_scan_block_id", "sent_morning", "sent_goodbye", "scan_log", "force_scan", "coins"]}
    with open(DATA_FILE, "w") as f: json.dump(serializable_data, f)

# --- TELEGRAM (TEXT ONLY) ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
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
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
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
        if 'Date' in df.columns: df = df.set_index('Date')
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for c in numeric_cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except Exception as e:
        print(f"Data Error: {e}")
        return pd.DataFrame()

# ==============================================================================
# 🧠 AI CHART (INTERNAL) & 5-D PROMPT
# ==============================================================================

def generate_ai_chart(df, coin_name):
    filename = f"ai_chart_{coin_name}.png"
    if len(df) < 30: return None
    try:
        mc = mpf.make_marketcolors(up='#00FF00', down='#FF0000', inherit=True)
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
        mpf.plot(df.tail(60), type='candle', style=s, volume=False, savefig=filename, figsize=(8, 5))
        return filename
    except: return None

# --- AI ANALYSIS (5-D FUSION LOGIC) ---
def analyze_with_vision(df, coin_name):
    ai_chart_path = generate_ai_chart(df, coin_name)
    if not ai_chart_path: return "NEUTRAL", 0, 0, 0, 0, 0, "Chart Error", None

    try:
        img = genai.upload_file(ai_chart_path)
        
        # --- THE MASTER PROMPT (5-D FUSION) ---
        prompt = """
        You are the "Crypto Campus AI" executing the '5-D Fusion' Strategy (Limit Order Setup).
        Analyze this 15-minute chart strictly according to these 7 STEPS:

        Step 1: Fundamentals & Sentiment
        - Check for extreme volatility candles (News impact). If chaotic, SKIP.

        Step 2: HTF & Malaysian SNR (The Map)
        - Trend: UP or DOWN?
        - Locate fresh Malaysian SNR (Support/RBS).
        - Look for Liquidity Pools (SSL/BSL) near the SNR.
        
        Step 3: The Trigger (ICT Time & Sweep)
        - Look for a Liquidity Sweep (Wick grab) of the SSL/BSL.
        - This is the "Fakeout". Did price grab liquidity and immediately reverse?

        Step 4: Confirmation (QML + MSS)
        - Did price displace (MSS) after the sweep?
        - Is there a QML pattern (Low -> High -> Lower Low -> Higher High)?

        Step 5: THE SNIPER EXECUTION (Golden Rule)
        - Identify the ICT FVG caused by the MSS.
        - Identify the Malaysian MPL (Quasimodo Left Shoulder Engulfing/Doji) inside that FVG.
        - CRITICAL: Use a LIMIT ORDER mentality. The entry must be at this MPL/FVG intersection.

        Step 6: Risk Management
        - Stop Loss must be TIGHT (just below the Sweep Wick).

        Step 7: Targets
        - TP1: Internal Liquidity.
        - TP2: H4 Resistance.
        - TP3: Swing High.
        - TP4: Moonbag.

        OUTPUT DECISION:
        Output ONLY a JSON string:
        {"signal": "LONG", "score": 90, "reason": "Liquidity Sweep + QML + MPL Limit Entry"}
        
        Score > 85 ONLY if the Step 5 (FVG + MPL Intersection) is clearly visible for a Limit Order.
        """
        
        response = model.generate_content([prompt, img])
        result = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        sig = result.get("signal", "NEUTRAL")
        score = int(result.get("score", 0))
        reason = result.get("reason", "AI Analysis")
        os.remove(ai_chart_path)
    except Exception as e:
        if os.path.exists(ai_chart_path): os.remove(ai_chart_path)
        return "NEUTRAL", 0, 0, 0, 0, 0, f"AI Err: {str(e)[:20]}", None

    curr_close = df['Close'].iloc[-1]
    atr = (df['High'].iloc[-1] - df['Low'].iloc[-1])
    sl = curr_close - (atr * 1.5) if sig == "LONG" else curr_close + (atr * 1.5)
    sl_dist = abs(curr_close - sl) / curr_close * 100
    leverage = int(max(5, min(RISK_PER_TRADE_ROI / sl_dist, 75))) if sl_dist > 0 else 20

    return (sig if score > 85 else "NEUTRAL"), score, curr_close, leverage, sl, 0, reason, None

# --- FORMATTING FUNCTION (UPDATED) ---
def format_vip_message(coin, sig, price, sl, tps, leverage):
    p_fmt = ".4f" if price < 50 else ".2f"
    
    roi_1 = round(abs(tps[0]-price)/price*100*leverage, 1)
    roi_2 = round(abs(tps[1]-price)/price*100*leverage, 1)
    roi_3 = round(abs(tps[2]-price)/price*100*leverage, 1)
    roi_4 = round(abs(tps[3]-price)/price*100*leverage, 1)
    sl_roi = round(abs(price-sl)/price*100*leverage, 1)
    risk = abs(price - sl); reward = abs(tps[3] - price)
    rr = round(reward / risk, 1) if risk > 0 else 0
    direction_text = "🟢Long" if sig == "LONG" else "🔴Short"

    msg = (
        f"💎<b>CRYPTO CAMPUS VIP (5-D FUSION)</b>💎\n\n"
        f"🌟 <b>{coin} USDT</b>\n\n"
        f"{direction_text}\n\n"
        f"🚀<b>Isolated</b>\n"
        f"📈<b>Leverage {leverage}X</b>\n\n"
        f"💥<b>Entry {price:{p_fmt}} (Limit Order)</b>\n\n"
        f"✅<b>Take Profit</b>\n\n"
        f"1️⃣ {tps[0]:{p_fmt}} ({roi_1}%) - <i>Safety First (Close 50%, SL to BE)</i>\n"
        f"2️⃣ {tps[1]:{p_fmt}} ({roi_2}%) - <i>Standard (Close 25%)</i>\n"
        f"3️⃣ {tps[2]:{p_fmt}} ({roi_3}%) - <i>Swing (Close 15%)</i>\n"
        f"4️⃣ {tps[3]:{p_fmt}} ({roi_4}%) - <i>Moonbag (Hold 10%)</i>\n\n"
        f"⭕ <b>Stop Loss {sl:{p_fmt}} ({sl_roi}%)</b>\n\n"
        f"📝 <b>RR 1:{rr}</b>\n\n"
        f"⚠️ <b>Margin Use 1%-5%(Trading Plan Use)</b>"
    )
    return msg

# ==============================================================================
# MAIN UI
# ==============================================================================
saved_data = load_data()
for k, v in saved_data.items():
    if k not in st.session_state: st.session_state[k] = v

st.sidebar.title("🎛️ Control Panel")
current_time = datetime.now(lz)
is_within_hours = START_HOUR <= current_time.hour < END_HOUR

status_color = "red"; status_text = "STOPPED 🔴"
if st.session_state.bot_active:
    if st.session_state.sent_goodbye: status_color = "orange"; status_text = "DAY ENDED 💤"
    elif not is_within_hours: status_color = "orange"; status_text = "SLEEPING 💤"
    else: status_color = "green"; status_text = "RUNNING 🟢"

st.sidebar.markdown(f"**Status:** :{status_color}[{status_text}]")
st.sidebar.caption(f"Time: {START_HOUR}:00 - {END_HOUR}:00")
st.sidebar.metric("Daily Signals", f"{st.session_state.daily_count} / {MAX_DAILY_SIGNALS}")

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START", use_container_width=True): st.session_state.bot_active = True; save_full_state(); st.rerun()
if col2.button("⏹️ STOP", use_container_width=True): st.session_state.bot_active = False; save_full_state(); st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚡ FORCE SCAN NOW", use_container_width=True): st.session_state.force_scan = True; st.rerun()
if st.sidebar.button("🔄 RESET LIMIT (Admin)", use_container_width=True):
    st.session_state.daily_count = 0; st.session_state.signaled_coins = []; st.session_state.sent_goodbye = False; st.session_state.sent_morning = False; save_full_state(); st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🪙 Coin Manager (120 Coins)")
new_coin = st.sidebar.text_input("Add Coin", "").upper()
if st.sidebar.button("➕ Add Coin"):
    if new_coin and new_coin not in st.session_state.coins: st.session_state.coins.append(new_coin); save_full_state(); st.rerun()
rem_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove"):
    if rem_coin in st.session_state.coins: st.session_state.coins.remove(rem_coin); save_full_state(); st.rerun()

# --- 5-D TEST BUTTON ---
st.sidebar.markdown("---")
if st.sidebar.button("📡 Test 5-D Signal (Text Only)", use_container_width=True):
    st.sidebar.info("Simulating 5-D Setup...")
    test_df = get_data("BTC")
    if not test_df.empty:
        price = test_df['Close'].iloc[-1]
        sl = price * 0.995 
        risk = abs(price - sl)
        tps = [price + risk*1.5, price + risk*3, price + risk*5, price + risk*8]
        lev = 50
        sig_type = "LONG"

        send_telegram("", is_sticker=True); time.sleep(1)
        msg = format_vip_message("BTC", sig_type, price, sl, tps, leverage=lev)
        send_telegram(msg)
        st.sidebar.success("Signal Sent!")
    else: st.sidebar.error("Failed to fetch BTC")

st.title("👻 GHOST PROTOCOL 8.3 : PERFECT 5-D")
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

        sig, score, price, leverage, sl, _, reason, _ = analyze_with_vision(df, coin)
        
        if sig != "NEUTRAL":
            status_area.markdown(f"🎯 **Signal Found!** Sending Alert for {coin}...")
            risk = abs(price - sl)
            tps = [price+risk*1.5, price+risk*3, price+risk*5, price+risk*8] if sig == "LONG" else [price-risk*1.5, price-risk*3, price-risk*5, price-risk*8]
            
            send_telegram("", is_sticker=True); time.sleep(2)
            msg = format_vip_message(coin, sig, price, sl, tps, leverage)
            send_telegram(msg)

            st.session_state.history.insert(0, {"Time": datetime.now(lz).strftime("%H:%M"), "Coin": coin, "Signal": sig})
            st.session_state.daily_count += 1; st.session_state.signaled_coins.append(coin); save_full_state()
            
            if st.session_state.daily_count >= MAX_DAILY_SIGNALS:
                status_area.info("🛑 Daily Limit Reached! Waiting 15 mins to send Goodbye...")
                time.sleep(900) 
                send_telegram("🚀 Good Bye Traders! අදට Signals දීලා ඉවරයි. අපි ආයිත් හෙට දවසේ සුපිරි Entries ටිකක් ගමු! 👋")
                st.session_state.sent_goodbye = True
                save_full_state()
                break
        
        time.sleep(3); progress_bar.progress((i + 1) / len(st.session_state.coins))
    st.rerun()

with tab1:
    if st.session_state.bot_active:
        if current_time.hour == START_HOUR and not st.session_state.sent_morning:
            send_telegram("☀️ Good Morning Traders! ඔයාලා හැමෝටම ජයග්‍රාහී සුබ දවසක් වේවා! 🚀")
            st.session_state.sent_morning = True; save_full_state()

        if current_time.hour >= END_HOUR:
            if not st.session_state.sent_goodbye:
                if st.session_state.daily_count > 0:
                    send_telegram("🚀 Good Night Traders! අදට Signals දීලා ඉවරයි. අපි ආයිත් හෙට දවසේ සුපිරි Entries ටිකක් ගමු! 👋")
                else:
                    send_telegram("🧬අද Market එකේ High Probability Setups තිබුනේ නෑ (Choppy Market). 📉\n\nහෙට අලුත් දවසකින් හමුවෙමු! Good Night Traders! 👋")
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
