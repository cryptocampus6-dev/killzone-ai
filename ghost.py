import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import yfinance as yf

# --- FIX: MATPLOTLIB HEADLESS MODE & ADVANCED PLOTTING ---
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
    serializable_data = {k: v for k, v in st.session_state.items() if k in ["bot_active", "daily_count", "last_reset_date", "signaled_coins", "history", "last_scan_block_id", "sent_morning", "sent_goodbye", "scan_log", "force_scan", "coins"]}
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
# 🎨 ADVANCED CHART GENERATION (THE PRO LOOK)
# ==============================================================================

# 1. Simple Chart for AI Analysis (Clean, no lines)
def generate_ai_chart(df, coin_name):
    filename = f"ai_chart_{coin_name}.png"
    if len(df) < 30: return None
    try:
        # Use a clean style for AI
        mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', inherit=True)
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
        mpf.plot(df.tail(60), type='candle', style=s, volume=False, title=f"{coin_name} - AI Input", savefig=filename, figsize=(8, 5))
        return filename
    except: return None

# 2. Pro Chart for Telegram (With Watermark, Entry, SL, TP lines)
def generate_telegram_chart(df, coin_name, signal_type, entry, sl, tps):
    filename = f"tg_chart_{coin_name}_{int(time.time())}.png"
    plot_df = df.tail(80) # Show a bit more history
    if len(plot_df) < 30: return None

    # Custom Style mimicking TradingView Dark
    mc = mpf.make_marketcolors(up='#089981', down='#F23645', edge='inherit', wick='inherit', volume='in', inherit=True)
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True, facecolor='#131722', figcolor='#131722', rc={'axes.labelcolor': 'white', 'xtick.color': 'white', 'ytick.color': 'white', 'text.color': 'white'})

    # Define Horizontal Lines (Entry, SL, TPs)
    hlines_data = [entry, sl] + tps
    # Colors: Entry(Blue), SL(Red), TPs(Green)
    hlines_colors = ['#2962FF', '#F23645'] + ['#089981'] * len(tps)
    hlines_styles = ['-'] + ['--'] * (len(tps) + 1) # Solid for Entry, dashed for others

    fig, axes = mpf.plot(plot_df, type='candle', style=s, volume=False,
                         hlines=dict(hlines=hlines_data, colors=hlines_colors, linewidths=1.5, linestyles=hlines_styles),
                         title=f"\n{coin_name} - 15m | {signal_type} Setup",
                         figsize=(12, 7), returnfig=True, tight_layout=True)
    
    ax_main = axes[0]

    # --- ADD LABELS ---
    p_fmt = ".2f" if entry > 50 else ".4f"
    
    # Entry Label
    ax_main.text(len(plot_df)+1, entry, f" Entry: {entry:{p_fmt}}", color='#2962FF', fontsize=10, fontweight='bold', va='center')
    
    # SL Label
    ax_main.text(len(plot_df)+1, sl, f" SL: {sl:{p_fmt}}", color='#F23645', fontsize=10, va='center')
    
    # TP Labels
    for i, tp_price in enumerate(tps):
        ax_main.text(len(plot_df)+1, tp_price, f" TP{i+1}: {tp_price:{p_fmt}}", color='#089981', fontsize=9, va='center')

    # --- ADD WATERMARK (CRYPTO CAMPUS) ---
    # Place in the center of the chart
    mid_x = len(plot_df) / 2
    mid_y = (plot_df['High'].max() + plot_df['Low'].min()) / 2
    ax_main.text(mid_x, mid_y, "CRYPTO CAMPUS", fontsize=40, color='white', 
                 alpha=0.15, ha='center', va='center', fontweight='bold', rotation=0, zorder=0)

    # Save the complex figure
    fig.savefig(filename, facecolor=fig.get_facecolor())
    plt.close(fig) # Close plot to free memory
    return filename

# --- AI ANALYSIS ---
def analyze_with_vision(df, coin_name):
    # Generate simple chart for AI
    ai_chart_path = generate_ai_chart(df, coin_name)
    if not ai_chart_path: return "NEUTRAL", 0, 0, 0, 0, 0, "Chart Error", None

    try:
        img = genai.upload_file(ai_chart_path)
        prompt = """
        You are an elite Crypto Trader (SMC/ICT/Price Action). Analyze this 15m chart.
        Look for: Liquidity Sweeps, MSS, Order Blocks, strong rejection wicks.
        Output ONLY JSON: {"signal": "LONG", "score": 90, "reason": "Brief reason"}
        Score > 85 for signal.
        """
        response = model.generate_content([prompt, img])
        result = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        sig = result.get("signal", "NEUTRAL")
        score = int(result.get("score", 0))
        reason = result.get("reason", "AI Analysis")
        os.remove(ai_chart_path) # Clean AI chart
    except Exception as e:
        if os.path.exists(ai_chart_path): os.remove(ai_chart_path)
        return "NEUTRAL", 0, 0, 0, 0, 0, f"AI Err: {str(e)[:20]}", None

    # Data for Signal
    curr_close = df['Close'].iloc[-1]
    atr = (df['High'].iloc[-1] - df['Low'].iloc[-1])
    # Logical SL placement (behind structure)
    sl = curr_close - (atr * 2.5) if sig == "LONG" else curr_close + (atr * 2.5)
    
    sl_dist = abs(curr_close - sl) / curr_close * 100
    leverage = int(max(5, min(RISK_PER_TRADE_ROI / sl_dist, 75))) if sl_dist > 0 else 20

    return (sig if score > 85 else "NEUTRAL"), score, curr_close, leverage, sl, 0, reason, None

# --- FORMATTING FUNCTION ---
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
        f"💎<b>CRYPTO CAMPUS VIP</b>💎\n\n🌟 <b>{coin} USDT</b>\n\n{direction_text}\n\n🚀<b>Isolated</b>\n📈<b>Leverage {leverage}X</b>\n\n💥<b>Entry {price:{p_fmt}}</b>\n\n✅<b>Take Profit</b>\n\n1️⃣ {tps[0]:{p_fmt}} ({roi_1}%)\n2️⃣ {tps[1]:{p_fmt}} ({roi_2}%)\n3️⃣ {tps[2]:{p_fmt}} ({roi_3}%)\n4️⃣ {tps[3]:{p_fmt}} ({roi_4}%)\n\n⭕ <b>Stop Loss {sl:{p_fmt}} ({sl_roi}%)</b>\n\n📝 <b>RR 1:{rr}</b>\n\n⚠️ <b>Margin Use 1%-5%(Trading Plan Use)</b>"
    )
    return msg

# ==============================================================================
# MAIN UI
# ==============================================================================
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

st.sidebar.markdown("---")
st.sidebar.subheader("🪙 Coin Manager")
new_coin = st.sidebar.text_input("Add Coin", "").upper()
if st.sidebar.button("➕ Add Coin"):
    if new_coin and new_coin not in st.session_state.coins: st.session_state.coins.append(new_coin); save_full_state(); st.rerun()
rem_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove"):
    if rem_coin in st.session_state.coins: st.session_state.coins.remove(rem_coin); save_full_state(); st.rerun()

# --- PRO TEST BUTTON ---
st.sidebar.markdown("---")
if st.sidebar.button("📡 Test Pro Chart & Signal", use_container_width=True):
    st.sidebar.info("Generating BTC Pro Chart...")
    test_df = get_data("BTC")
    if not test_df.empty:
        # Generate Test Signal Data
        price = test_df['Close'].iloc[-1]
        sl = price * 0.99 # 1% SL
        risk = abs(price - sl)
        tps = [price + risk*1, price + risk*2, price + risk*3, price + risk*4]
        lev = 50
        sig_type = "LONG"

        # GENERATE THE PRO CHART
        tg_chart_path = generate_telegram_chart(test_df, "BTC", sig_type, price, sl, tps)
        
        if tg_chart_path:
            send_telegram("", is_sticker=True); time.sleep(1)
            msg = format_vip_message("BTC", sig_type, price, sl, tps, leverage=lev)
            send_telegram(msg, image_path=tg_chart_path)
            st.sidebar.success("Pro Signal Sent!")
            os.remove(tg_chart_path) # Clean up
        else: st.sidebar.error("Failed to generate Pro Chart")
    else: st.sidebar.error("Failed to fetch BTC")

# --- MAIN ---
st.title("👻 GHOST PROTOCOL 5.2 : PRO CHARTING")
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

        # 1. AI Analysis (uses simple chart internally)
        sig, score, price, leverage, sl, _, reason, _ = analyze_with_vision(df, coin)
        
        if sig != "NEUTRAL":
            status_area.markdown(f"🎯 **Signal Found!** Generating Pro Chart for {coin}...")
            # TP calc
            risk = abs(price - sl)
            if sig == "LONG": tps = [price+risk, price+2*risk, price+3*risk, price+4*risk]
            else: tps = [price-risk, price-2*risk, price-3*risk, price-4*risk]
            
            # 2. Generate PRO Chart for Telegram
            tg_chart_path = generate_telegram_chart(df, coin, sig, price, sl, tps)

            if tg_chart_path:
                send_telegram("", is_sticker=True); time.sleep(2)
                msg = format_vip_message(coin, sig, price, sl, tps, leverage)
                send_telegram(msg, image_path=tg_chart_path)
                os.remove(tg_chart_path) # Clean up chart

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
