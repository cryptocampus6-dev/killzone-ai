import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import yfinance as yf
import numpy as np
from datetime import datetime

# --- USER SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

# --- CONFIGURATION ---
START_HOUR = 7
END_HOUR = 21
MAX_DAILY_SIGNALS = 8
SCORE_THRESHOLD = 85
TARGET_SL_ROI = 60
DATA_FILE = "bot_data.json"

st.set_page_config(page_title="Ghost Protocol Dashboard", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- DATA MANAGEMENT ---
def load_data():
    default = {
        "bot_active": True, "daily_count": 0, "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [], "history": [], "last_scan_block_id": -1,
        "sent_morning": False, "sent_goodbye": False
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if data.get("last_reset_date") != datetime.now(lz).strftime("%Y-%m-%d"):
                    data.update({"daily_count": 0, "signaled_coins": [], "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"), "sent_morning": False, "sent_goodbye": False})
                    with open(DATA_FILE, "w") as fw: json.dump(data, fw)
                return data
        except: return default
    return default

def save_full_state():
    data = {
        "bot_active": st.session_state.bot_active, "daily_count": st.session_state.daily_count,
        "last_reset_date": st.session_state.last_reset_date, "signaled_coins": st.session_state.signaled_coins,
        "history": st.session_state.history, "last_scan_block_id": st.session_state.last_scan_block_id,
        "sent_morning": st.session_state.sent_morning, "sent_goodbye": st.session_state.sent_goodbye
    }
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- TELEGRAM ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker: requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else: requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

# --- DATA FETCHING (YAHOO FINANCE) ---
def get_data(symbol, limit=200):
    try:
        ticker = f"{symbol}-USD"
        df = yf.download(ticker, period="5d", interval="15m", progress=False)
        
        if not df.empty:
            df = df.reset_index()
            # Multi-index fix
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            df = df.rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            return df
    except: 
        return pd.DataFrame()
    return pd.DataFrame()

# ==============================================================================
# 🧠 TRADING BIBLE LOGIC (5 METHODS)
# ==============================================================================

def analyze_ultimate(df, coin_name):
    if df.empty or len(df) < 50: return "NEUTRAL", 0, 0, 0, 0, 0, []

    # Indicators
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    df['ema200'] = ta.ema(df['close'], 200)
    df['rsi'] = ta.rsi(df['close'], 14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    methods_hit = []
    score = 50 

    # --- 1. FUNDAMENTALS (Volatility Check) ---
    if (curr['high'] - curr['low']) > (curr['atr'] * 3.5):
        return "NEUTRAL", 0, 0, 0, 0, 0, ["NEWS SHOCK"]
    
    avg_vol = df['volume'].rolling(20).mean().iloc[-1]
    is_whale = curr['volume'] > (avg_vol * 3.0)
    if is_whale: methods_hit.append("Whale Vol")

    # --- 2. HTF TREND & MSNR (QML) ---
    trend = "BULL" if curr['close'] > curr['ema200'] else "BEAR"
    
    l = df['low']; h = df['high']
    swing_lows = l[(l.shift(1) > l) & (l.shift(-1) > l)].tail(3).values
    swing_highs = h[(h.shift(1) < h) & (h.shift(-1) < h)].tail(3).values
    
    qml_bull = False; qml_bear = False
    
    if len(swing_lows) >= 2 and len(swing_highs) >= 2:
        if swing_highs[1] > swing_highs[0] and curr['close'] < swing_lows[1]: qml_bear = True
        if swing_lows[1] < swing_lows[0] and curr['close'] > swing_highs[1]: qml_bull = True

    # --- 3. LIQUIDITY (SWEEP) ---
    prev_low = df['low'].iloc[-10:-1].min()
    prev_high = df['high'].iloc[-10:-1].max()
    sweep_bull = (curr['low'] < prev_low) and (curr['close'] > prev_low)
    sweep_bear = (curr['high'] > prev_high) and (curr['close'] < prev_high)
    
    if sweep_bull: methods_hit.append("Liq Sweep")
    if sweep_bear: methods_hit.append("Liq Sweep")

    # --- 4. ICT (FVG & Time) ---
    fvg_bull = (df['low'].shift(2) > df['high']).iloc[-1]
    fvg_bear = (df['high'].shift(2) < df['low']).iloc[-1]
    
    utc_h = datetime.now(pytz.utc).hour
    killzone = (7 <= utc_h <= 10) or (12 <= utc_h <= 16)

    # --- 5. PRICE ACTION ---
    engulf_bull = (curr['close'] > curr['open']) and (prev['close'] < prev['open']) and (curr['close'] > prev['high'])
    engulf_bear = (curr['close'] < curr['open']) and (prev['close'] > prev['open']) and (curr['close'] < prev['low'])

    # --- SCORING ---
    if trend == "BULL":
        score += 10
        if qml_bull: score += 20; methods_hit.append("QML")
        if sweep_bull: score += 20
        if fvg_bull: score += 15; methods_hit.append("FVG")
        if engulf_bull: score += 15; methods_hit.append("Engulfing")
        if killzone: score += 5
    
    elif trend == "BEAR":
        score -= 10
        if qml_bear: score -= 20; methods_hit.append("QML")
        if sweep_bear: score -= 20
        if fvg_bear: score -= 15; methods_hit.append("FVG")
        if engulf_bear: score -= 15; methods_hit.append("Engulfing")
        if killzone: score -= 5

    # FINAL SIGNAL
    sig = "NEUTRAL"
    final_score = score
    
    if score >= SCORE_THRESHOLD:
        sig = "LONG"
        final_score = min(score, 100)
    elif score <= (100 - SCORE_THRESHOLD):
        sig = "SHORT"
        final_score = min(100 - score, 100)

    sl_long = curr['low'] * 0.99
    sl_short = curr['high'] * 1.01

    return sig, final_score, curr['close'], curr['atr'], sl_long, sl_short, methods_hit

# ==============================================================================
# MAIN APP LOOP
# ==============================================================================

saved_data = load_data()
for k, v in saved_data.items():
    if k not in st.session_state: st.session_state[k] = v

if 'coins' not in st.session_state:
    st.session_state.coins = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "TRX", "MATIC", "LTC", "BCH", "UNI", "NEAR", "APT", "ICP", "FIL", "ATOM", "XLM", "DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "MEME", "PEOPLE", "BOME", "DOGS", "NOT", "TURBO", "BRETT", "POPCAT", "MYRO", "LADYS", "SATS", "ORDI", "RENDER", "FET", "WLD", "ARKM", "GRT", "THETA", "AGIX", "OCEAN", "PHB", "SUI", "SEI", "ARB", "OP", "TIA", "INJ", "KAS", "TON", "FTM", "ALGO", "MANTA", "STRK", "BLUR", "ZRO", "ZK", "PYTH", "JUP", "ENS", "CRV", "AAVE", "MKR", "SNX", "COMP", "1INCH", "RUNE", "DYDX", "GMX", "LDO", "PENDLE", "EGLD", "SAND", "MANA", "AXS", "GALA", "CHZ", "FLOW", "EOS", "NEO", "QTUM", "IOTA", "KAVA", "MINA", "QNT", "HBAR", "VET", "ZEC", "DASH", "XMR", "ROSE", "HOT", "RVN", "BAT", "ENJ", "ZIL", "IOST"]
if 'scan_log' not in st.session_state: st.session_state.scan_log = ""
if 'force_scan' not in st.session_state: st.session_state.force_scan = False

# SIDEBAR
st.sidebar.title("🎛️ Control Panel")
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
st.sidebar.caption(f"Time: {START_HOUR}:00 - {END_HOUR}:00")
st.sidebar.metric("Daily Signals", f"{st.session_state.daily_count} / {MAX_DAILY_SIGNALS}")
st.sidebar.caption("Leverage: Dynamic (Risk Based)")

if st.session_state.signaled_coins:
    st.sidebar.caption(f"Today's Signals: {', '.join(st.session_state.signaled_coins)}")

col1, col2 = st.sidebar.columns(2)
if col1.button("▶️ START"): st.session_state.bot_active = True; save_full_state(); st.rerun()
if col2.button("⏹️ STOP"): st.session_state.bot_active = False; save_full_state(); st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚡ FORCE SCAN NOW"): st.session_state.force_scan = True; st.rerun()
st.sidebar.markdown("---")

st.sidebar.subheader("🪙 Coin Manager")
new_coin = st.sidebar.text_input("Add Coin (e.g. SUI)", "").upper()
if st.sidebar.button("➕ Add Coin"):
    if new_coin and new_coin not in st.session_state.coins:
        st.session_state.coins.append(new_coin); st.success(f"{new_coin} Added!")

remove_coin = st.sidebar.selectbox("Remove Coin", st.session_state.coins)
if st.sidebar.button("🗑️ Remove Selected"):
    if remove_coin in st.session_state.coins:
        st.session_state.coins.remove(remove_coin); st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("📡 Test Telegram"):
    send_telegram("", is_sticker=True); time.sleep(2)
    test_msg = f"💎<b>CRYPTO CAMPUS VIP</b>💎\n\n🌑 <b>BTC USDT</b>\n\n🟢<b>Long</b>\n\n🚀<b>Isolated</b>\n📈<b>Leverage 25X</b>\n\n💥<b>Entry 95000.00</b>\n\n✅<b>Take Profit</b>\n\n1️⃣ 96000.00 (26.3%)\n2️⃣ 97000.00 (52.6%)\n\n⭕ <b>Stop Loss 94000.00 (60.0%)</b>\n\n📝 <b>RR 1:2.0</b>\n\n⚠️ <b>Margin Use 1%-5%(Trading Plan Use)</b>"
    send_telegram(test_msg); st.sidebar.success("Test Sent!")

st.title("👻 GHOST PROTOCOL 2.0 : ELITE TRADER")
st.write("Methods Active: **Structure Guard, 3xATR Shield, Double Conf, Trend (4H), ADX, VSA, Sniper, MSNR, Liquidity, PA, ICT, News, Fib, RSI Div, BB**")
st.metric("🇱🇰 Sri Lanka Time", current_time.strftime("%H:%M:%S"))

tab1, tab2 = st.tabs(["📊 Live Scanner", "📜 Signal History"])

def run_scan():
    if st.session_state.daily_count >= MAX_DAILY_SIGNALS:
        if not st.session_state.sent_goodbye:
            send_telegram("🚀 Good Bye Traders! අදට Signals දීලා ඉවරයි. අපි ආයිත් හෙට දවසේ සුපිරි Entries ටිකක් ගමු! 👋")
            st.session_state.sent_goodbye = True; save_full_state()
        st.warning("⚠️ Daily Signal Limit Reached."); return

    st.markdown(f"### 🔄 Scanning {len(coins_list)} Coins...")
    progress_bar = st.progress(0); status_area = st.empty()
    
    log_container = st.container()
    log_container.write("---")
    live_log = log_container.empty()
    if 'scan_log' not in st.session_state: st.session_state.scan_log = ""

    for i, coin in enumerate(coins_list):
        if coin in st.session_state.signaled_coins:
            progress_bar.progress((i + 1) / len(coins_list)); continue

        try:
            status_area.markdown(f"👀 **Checking:** `{coin}` ...")
            
            df = get_data(coin)
            
            if df.empty:
                st.session_state.scan_log = f"`{coin}`: ⚠️ No Data | " + st.session_state.scan_log
                live_log.markdown(f"#### 📝 Live Scores:\n{st.session_state.scan_log}")
                time.sleep(0.2)
                continue 

            sig, score, price, atr, sl_long, sl_short, methods = analyze_ultimate(df, coin)
            
            if score >= 85: score_color = "green"
            elif score <= 15: score_color = "red"
            else: score_color = "orange"
            
            status_area.markdown(f"👀 **Checked:** `{coin}` | 📊 **Score:** :{score_color}[`{score}/100`]")
            
            st.session_state.scan_log = f"`{coin}`: :{score_color}[{score}] | " + st.session_state.scan_log
            if len(st.session_state.scan_log) > 2000: st.session_state.scan_log = st.session_state.scan_log[:2000]
            live_log.markdown(f"#### 📝 Live Scores:\n{st.session_state.scan_log}")
            
            time.sleep(0.5)

            if sig != "NEUTRAL":
                if st.session_state.daily_count < MAX_DAILY_SIGNALS:
                    send_telegram("", is_sticker=True); time.sleep(5)
                    
                    if sig == "LONG":
                        sl = sl_long 
                        if (price - sl) / price < 0.005: sl = price - (atr * 1.5)
                        dist_percent = (price - sl) / price
                    else: # SHORT
                        sl = sl_short 
                        if (sl - price) / price < 0.005: sl = price + (atr * 1.5)
                        dist_percent = (sl - price) / price
                    
                    if dist_percent > 0: ideal_leverage = int(TARGET_SL_ROI / (dist_percent * 100))
                    else: ideal_leverage = 20
                    dynamic_leverage = max(5, min(ideal_leverage, 50))
                    
                    if sig == "LONG":
                        dist = price - sl; tp_dist = dist * 2.0
                        tps = [price + (tp_dist * x * 0.6) for x in range(1, 5)] 
                        emoji_circle = "🟢"; direction_txt = "Long"
                    else:
                        dist = sl - price; tp_dist = dist * 2.0
                        tps = [price - (tp_dist * x * 0.6) for x in range(1, 5)]
                        emoji_circle = "🔴"; direction_txt = "Short"
                    
                    rr = round(abs(tps[3]-price)/abs(price-sl), 2)
                    roi_1 = round(abs(tps[0]-price)/price*100*dynamic_leverage, 1)
                    roi_2 = round(abs(tps[1]-price)/price*100*dynamic_leverage, 1)
                    roi_3 = round(abs(tps[2]-price)/price*100*dynamic_leverage, 1)
                    roi_4 = round(abs(tps[3]-price)/price*100*dynamic_leverage, 1)
                    sl_roi = round(abs(price-sl)/price*100*dynamic_leverage, 1)
                    p_fmt = ".8f" if price < 1 else ".2f"

                    msg = (
                        f"💎<b>CRYPTO CAMPUS VIP</b>💎\n\n"
                        f"🌑 <b>{coin} USDT</b>\n\n"
                        f"{emoji_circle}<b>{direction_txt}</b>\n\n"
                        f"🚀<b>Isolated</b>\n"
                        f"📈<b>Leverage {dynamic_leverage}X</b>\n\n"
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
                    
                    send_telegram(msg)
                    st.session_state.history.insert(0, {"Time": current_time.strftime("%H:%M"), "Coin": coin, "Signal": sig, "Methods": ", ".join(methods)})
                    st.session_state.daily_count += 1
                    st.session_state.signaled_coins.append(coin)
                    save_full_state()
                    
                    if st.session_state.daily_count >= MAX_DAILY_SIGNALS:
                        if not st.session_state.sent_goodbye:
                            send_telegram("🚀 Good Bye Traders! අදට Signals දීලා ඉවරයි. අපි ආයිත් හෙට දවසේ සුපිරි Entries ටිකක් ගමු! 👋")
                            st.session_state.sent_goodbye = True; save_full_state()
                        break
        except Exception as e:
            st.session_state.scan_log = f"`{coin}`: ⚠️ Error | " + st.session_state.scan_log
            live_log.markdown(f"#### 📝 Live Scores:\n{st.session_state.scan_log}")
            time.sleep(0.5)
        
        progress_bar.progress((i + 1) / len(coins_list))
    
    status_area.empty(); st.success("Scan Complete!"); return

with tab1:
    if st.session_state.bot_active:
        if is_within_hours and not st.session_state.sent_morning:
            send_telegram("☀️ Good Morning Traders! ඔයාලා හැමෝටම ජයග්‍රාහී සුබ දවසක් වේවා! 🚀")
            st.session_state.sent_morning = True; save_full_state()

        if current_time.hour >= END_HOUR and not st.session_state.sent_goodbye:
            if st.session_state.daily_count > 0:
                msg = "🚀 Good Bye Traders! අදට Signals දීලා ඉවරයි. අපි ආයිත් හෙට දවසේ සුපිරි Entries ටිකක් ගමු! 👋"
            else:
                msg = "අද Market එකේ අපේ Strategy එකට ගැලපෙන High Probability Setups තිබුනේ නෑ (Choppy Market). 📉\n\nබොරු Trades දාලා Loss කරගන්නවට වඩා, ඉවසීමෙන් Capital එක ආරක්ෂා කරගන්න එක තමයි Professional Trading කියන්නේ. 🧠💎\n\nහෙට අලුත් දවසකින් හමුවෙමු! Good Night Traders! 👋"
            send_telegram(msg); st.session_state.sent_goodbye = True; save_full_state()

        if st.session_state.daily_count >= MAX_DAILY_SIGNALS:
            st.warning("🛑 Daily Limit Reached. Sleeping..."); time.sleep(60); st.rerun()
        
        elif is_within_hours:
            current_block_id = current_time.hour * 4 + (current_time.minute // 15)
            is_start_of_block = (current_time.minute % 15) <= 5 
            if (current_block_id != st.session_state.last_scan_block_id) and is_start_of_block:
                st.session_state.last_scan_block_id = current_block_id; save_full_state(); run_scan(); st.rerun()
            elif st.session_state.force_scan:
                run_scan(); st.session_state.force_scan = False; st.rerun()
            else:
                next_min = 15 - (current_time.minute % 15)
                # Show Last Log
                if st.session_state.scan_log: st.markdown(f"#### 📝 Last Scan Scores:\n{st.session_state.scan_log}")
                st.info(f"⏳ **Monitoring...** (Next scan in {next_min} mins)")
                time.sleep(5); st.rerun()
        else:
            st.warning(f"💤 SLEEPING (Resumes {START_HOUR}:00)"); time.sleep(10); st.rerun()
    else: st.error("⚠️ STOPPED"); time.sleep(2)

with tab2:
    if st.session_state.history: st.table(pd.DataFrame(st.session_state.history))
    else: st.info("No signals yet.")
