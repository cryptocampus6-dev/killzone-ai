import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import numpy as np
from datetime import datetime

# --- USER SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAG7YAYrzt9HYu34UhUJ0af_TDamhyndBas"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWlMq--iOTVBE4BA"

# --- TIME SETTINGS ---
START_HOUR = 7    
END_HOUR = 21     
MAX_DAILY_SIGNALS = 8 

# --- METHOD CONFIG ---
SCORE_THRESHOLD = 85   

# --- DYNAMIC SETTINGS ---
MAX_LEVERAGE = 50  
TARGET_SL_ROI = 60 

DATA_FILE = "bot_data.json" 

st.set_page_config(page_title="Ghost Protocol Dashboard", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- ADVANCED MEMORY SYSTEM (JSON) ---
def load_data():
    default_data = {
        "bot_active": True,
        "daily_count": 0,
        "last_reset_date": datetime.now(lz).strftime("%Y-%m-%d"),
        "signaled_coins": [],
        "history": [],
        "last_scan_block_id": -1,
        "sent_morning": False,
        "sent_goodbye": False
    }
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data
        except:
            return default_data
    return default_data

def save_data(key, value):
    current_data = load_data()
    current_data[key] = value
    with open(DATA_FILE, "w") as f:
        json.dump(current_data, f)

def save_full_state():
    data_to_save = {
        "bot_active": st.session_state.bot_active,
        "daily_count": st.session_state.daily_count,
        "last_reset_date": st.session_state.last_reset_date,
        "signaled_coins": st.session_state.signaled_coins,
        "history": st.session_state.history,
        "last_scan_block_id": st.session_state.last_scan_block_id,
        "sent_morning": st.session_state.sent_morning,
        "sent_goodbye": st.session_state.sent_goodbye
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data_to_save, f)

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

# --- ROBUST DATA FETCHING (FIXED NO DATA ISSUE) ---
def get_data(symbol, limit=200, timeframe='15m'):
    headers = {"User-Agent": "Mozilla/5.0"}
    # Try Binance US first (Works on Cloud)
    try:
        url = "https://api.binance.us/api/v3/klines"
        params = {'symbol': symbol.replace('/', '').replace(':USDT', ''), 'interval': timeframe, 'limit': limit}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'c', 'q', 'n', 'tb', 'tq', 'i'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            cols = ['open', 'high', 'low', 'close', 'volume']
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            return df
    except: pass

    # Fallback to MEXC
    try:
        url = "https://api.mexc.com/api/v3/klines"
        symbol_mexc = symbol.replace('/', '').replace(':USDT', '')
        params = {'symbol': symbol_mexc, 'interval': timeframe, 'limit': limit}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'c', 'q', 'n', 'tb', 'tq', 'i'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            cols = ['open', 'high', 'low', 'close', 'volume']
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            return df
    except: pass
    
    return pd.DataFrame()

# --- METHOD 9: NEWS IMPACT CHECK ---
def check_news_impact(btc_df):
    if btc_df.empty: return False
    curr = btc_df.iloc[-1]
    # Simple ATR based Volatility Check
    tr = max(curr['high'] - curr['low'], abs(curr['high'] - curr['open']))
    if tr > (curr['open'] * 0.02): return True 
    return False

# ==============================================================================
# 🧠 NEW ULTIMATE LOGIC (REPLACING THE OLD 13 METHODS)
# ==============================================================================

# --- A. MALAYSIAN SNR: QML ---
def detect_qml(df):
    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])]
    
    last_highs = df['swing_high'].dropna().tail(2).values
    last_lows = df['swing_low'].dropna().tail(2).values
    
    qml_bearish, qml_bullish = False, False
    
    if len(last_highs) >= 2 and len(last_lows) >= 2:
        if last_highs[1] > last_highs[0] and df['close'].iloc[-1] < last_lows[1]: qml_bearish = True
        if last_lows[1] < last_lows[0] and df['close'].iloc[-1] > last_highs[1]: qml_bullish = True
            
    return qml_bullish, qml_bearish

# --- B. ICT & C. CRT ---
def detect_ict_crt(df):
    bullish_fvg = (df['low'].shift(2) > df['high']) 
    bearish_fvg = (df['high'].shift(2) < df['low'])
    
    ref_high = df['high'].shift(5)
    ref_low = df['low'].shift(5)
    
    body_break_up = df['close'].iloc[-1] > ref_high.iloc[-1]
    body_break_down = df['close'].iloc[-1] < ref_low.iloc[-1]
    
    return bullish_fvg.iloc[-1], bearish_fvg.iloc[-1], body_break_up, body_break_down

# --- MASTER ANALYSIS FUNCTION (Keeping Old Signature) ---
def analyze_ultimate(df, coin_name):
    if df.empty or len(df) < 50: return "NEUTRAL", 0, 0, 0, 0, 0, []

    # Indicators for return
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    curr = df.iloc[-1]
    
    # 2. Killzones
    current_hour = datetime.now(pytz.utc).hour
    is_killzone = (7 <= current_hour <= 17) or (12 <= current_hour <= 22)

    # 3. Run Methods
    qml_buy, qml_sell = detect_qml(df)
    fvg_buy, fvg_sell, crt_buy, crt_sell = detect_ict_crt(df)

    methods_hit = []
    
    # --- BUY SCORE ---
    buy_score = 0
    if qml_buy: buy_score += 35; methods_hit.append("QML Buy")
    if fvg_buy: buy_score += 25; methods_hit.append("ICT FVG")
    if crt_buy: buy_score += 20; methods_hit.append("Body Break")
    if is_killzone: buy_score += 10
    
    # --- SELL SCORE ---
    sell_score = 0
    if qml_sell: sell_score += 35; methods_hit.append("QML Sell")
    if fvg_sell: sell_score += 25; methods_hit.append("ICT FVG")
    if crt_sell: sell_score += 20; methods_hit.append("Body Break")
    if is_killzone: sell_score += 10

    # Final Signal Determination
    final_score = 50 
    sig = "NEUTRAL"

    if buy_score >= 85:
        final_score = buy_score if buy_score <= 100 else 99
        sig = "LONG"
    elif sell_score >= 85:
        final_score = 100 - sell_score 
        if final_score < 0: final_score = 1
        sig = "SHORT"

    # Calculate SL Levels 
    swing_low = df['low'].tail(10).min()
    swing_high = df['high'].tail(10).max()
    
    sl_long = swing_low * 0.995 
    sl_short = swing_high * 1.005

    return sig, final_score, curr['close'], curr['atr'], sl_long, sl_short, methods_hit

# ==============================================================================
# MAIN APP LOOP (UNCHANGED UI - ONLY LOGIC FIXED)
# ==============================================================================

# --- SESSION STATE INITIALIZATION & RESET FIX ---
saved_data = load_data()
current_date_str = datetime.now(lz).strftime("%Y-%m-%d")

# 🔴 FIX: Force Reset if Date Changed
if saved_data['last_reset_date'] != current_date_str:
    saved_data['daily_count'] = 0
    saved_data['signaled_coins'] = []
    saved_data['last_reset_date'] = current_date_str
    saved_data['sent_morning'] = False
    saved_data['sent_goodbye'] = False
    with open(DATA_FILE, "w") as f:
        json.dump(saved_data, f)

if 'bot_active' not in st.session_state: st.session_state.bot_active = saved_data['bot_active']
if 'daily_count' not in st.session_state: st.session_state.daily_count = saved_data['daily_count']
if 'last_reset_date' not in st.session_state: st.session_state.last_reset_date = saved_data['last_reset_date']
if 'signaled_coins' not in st.session_state: st.session_state.signaled_coins = saved_data['signaled_coins']
if 'history' not in st.session_state: st.session_state.history = saved_data['history']
if 'last_scan_block_id' not in st.session_state: st.session_state.last_scan_block_id = saved_data['last_scan_block_id']
if 'sent_morning' not in st.session_state: st.session_state.sent_morning = saved_data['sent_morning']
if 'sent_goodbye' not in st.session_state: st.session_state.sent_goodbye = saved_data['sent_goodbye']

# 🔴 FIX: Ensure Session State matches Cleaned Data
if st.session_state.last_reset_date != current_date_str:
    st.session_state.daily_count = 0
    st.session_state.signaled_coins = []
    st.session_state.last_reset_date = current_date_str
    st.session_state.sent_morning = False
    st.session_state.sent_goodbye = False
    save_full_state()

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
if 'force_scan' not in st.session_state: st.session_state.force_scan = False

# --- SIDEBAR ---
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
if col1.button("▶️ START"):
    st.session_state.bot_active = True; save_full_state(); st.rerun()
if col2.button("⏹️ STOP"):
    st.session_state.bot_active = False; save_full_state(); st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("⚡ FORCE SCAN NOW"):
    st.session_state.force_scan = True; st.rerun()
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
            st.session_state.sent_goodbye = True
            save_full_state()
        st.warning("⚠️ Daily Signal Limit Reached."); return

    try:
        btc_df = get_data("BTCUSDT", limit=50)
        if check_news_impact(btc_df):
            st.error("🚨 HIGH VOLATILITY / NEWS DETECTED! SCAN PAUSED.")
            return
    except: pass

    st.markdown(f"### 🔄 Scanning {len(coins_list)} Coins...")
    progress_bar = st.progress(0); status_area = st.empty()
    
    for i, coin in enumerate(coins_list):
        if coin in st.session_state.signaled_coins:
            progress_bar.progress((i + 1) / len(coins_list)); continue

        try:
            status_area.markdown(f"👀 **Checking:** `{coin}` ...")
            
            df = get_data(f"{coin}USDT")
            
            if df.empty:
                status_area.markdown(f"⚠️ **Error:** `{coin}` (Failed to Fetch Data)")
                time.sleep(0.5) 
                continue 

            sig, score, price, atr, sl_long, sl_short, methods = analyze_ultimate(df, coin)
            
            # Color logic for 85 threshold
            score_color = "green" if score >= 85 else "red" if score <= 15 else "orange"
            
            status_area.markdown(f"👀 **Checked:** `{coin}` | 📊 **Score:** :{score_color}[`{score}/100`]")
            time.sleep(0.5) 

            if sig != "NEUTRAL":
                if st.session_state.daily_count < MAX_DAILY_SIGNALS:
                    send_telegram("", is_sticker=True); time.sleep(15)
                    
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
                    
                    dynamic_leverage = max(5, min(ideal_leverage, MAX_LEVERAGE))
                    
                    if sig == "LONG":
                        dist = price - sl
                        tp_dist = dist * 2.0
                        tps = [price + (tp_dist * x * 0.6) for x in range(1, 5)] 
                        emoji_circle = "🟢"; direction_txt = "Long"
                    else:
                        dist = sl - price
                        tp_dist = dist * 2.0
                        tps = [price - (tp_dist * x * 0.6) for x in range(1, 5)]
                        emoji_circle = "🔴"; direction_txt = "Short"
                    
                    rr = round(abs(tps[3]-price)/abs(price-sl), 2)
                    
                    roi_1 = round(abs(tps[0]-price)/price*100*dynamic_leverage, 1)
                    roi_2 = round(abs(tps[1]-price)/price*100*dynamic_leverage, 1)
                    roi_3 = round(abs(tps[2]-price)/price*100*dynamic_leverage, 1)
                    roi_4 = round(abs(tps[3]-price)/price*100*dynamic_leverage, 1)
                    sl_roi = round(abs(price-sl)/price*100*dynamic_leverage, 1)
                    
                    methods_str = ", ".join(methods)
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
                    st.session_state.history.insert(0, {"Time": current_time.strftime("%H:%M"), "Coin": coin, "Signal": sig, "Methods": methods_str})
                    st.session_state.daily_count += 1
                    st.session_state.signaled_coins.append(coin)
                    save_full_state()
                    
                    if st.session_state.daily_count >= MAX_DAILY_SIGNALS:
                        if not st.session_state.sent_goodbye:
                            send_telegram("🚀 Good Bye Traders! අදට Signals දීලා ඉවරයි. අපි ආයිත් හෙට දවසේ සුපිරි Entries ටිකක් ගමු! 👋")
                            st.session_state.sent_goodbye = True
                            save_full_state()
                        break
        
        except Exception as e:
            status_area.markdown(f"⚠️ **Error:** `{coin}` - {str(e)}")
            time.sleep(1) 
        
        progress_bar.progress((i + 1) / len(coins_list))
    
    status_area.empty(); st.success("Scan Complete!"); return

with tab1:
    if st.session_state.bot_active:
        if is_within_hours and not st.session_state.sent_morning:
            send_telegram("☀️ Good Morning Traders! ඔයාලා හැමෝටම ජයග්‍රාහී සුබ දවසක් වේවා! 🚀")
            st.session_state.sent_morning = True
            save_full_state()

        if current_time.hour >= END_HOUR and not st.session_state.sent_goodbye:
            if st.session_state.daily_count > 0:
                msg = "🚀 Good Bye Traders! අදට Signals දීලා ඉවරයි. අපි ආයිත් හෙට දවසේ සුපිරි Entries ටිකක් ගමු! 👋"
            else:
                msg = "🛑 **Market Update:** අද Market එකේ අපේ Strategy එකට ගැලපෙන High Probability Setups තිබුනේ නෑ (Choppy Market). 📉\n\nබොරු Trades දාලා Loss කරගන්නවට වඩා, ඉවසීමෙන් Capital එක ආරක්ෂා කරගන්න එක තමයි Professional Trading කියන්නේ. 🧠💎\n\nහෙට අලුත් දවසකින් හමුවෙමු! Good Night Traders! 👋"
            
            send_telegram(msg)
            st.session_state.sent_goodbye = True
            save_full_state()

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
                st.info(f"⏳ **Monitoring...** (Next scan in {next_min} mins)")
                time.sleep(5); st.rerun()
        else:
            st.warning(f"💤 SLEEPING (Resumes {START_HOUR}:00)"); time.sleep(10); st.rerun()
    else:
        st.error("⚠️ STOPPED"); time.sleep(2)

with tab2:
    if st.session_state.history: st.table(pd.DataFrame(st.session_state.history))
    else: st.info("No signals yet.")
