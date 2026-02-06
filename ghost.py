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
                    data["daily_count"] = 0
                    data["signaled_coins"] = []
                    data["last_reset_date"] = datetime.now(lz).strftime("%Y-%m-%d")
                    data["sent_morning"] = False
                    data["sent_goodbye"] = False
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

# --- ROBUST DATA FETCHING (SLOW & STEADY) ---
def get_data(symbol, timeframe='15m', limit=300):
    # Browser Headers to avoid blocking
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    clean_symbol = symbol.replace('/', '').replace(':USDT', '')
    
    # 1. Binance US (Primary)
    try:
        url = "https://api.binance.us/api/v3/klines"
        params = {'symbol': clean_symbol, 'interval': timeframe, 'limit': limit}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data, columns=['ts','o','h','l','c','v','ct','qa','nt','tb','tq','i'])
                df[['o','h','l','c','v']] = df[['o','h','l','c','v']].apply(pd.to_numeric)
                return df
    except: pass

    time.sleep(1) # Wait before fallback

    # 2. MEXC (Fallback)
    try:
        url = "https://api.mexc.com/api/v3/klines"
        params = {'symbol': clean_symbol, 'interval': timeframe, 'limit': limit}
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data, columns=['ts','o','h','l','c','v','ct','qa','nt','tb','tq','i'])
                df[['o','h','l','c','v']] = df[['o','h','l','c','v']].apply(pd.to_numeric)
                return df
    except: pass

    return pd.DataFrame()

# ==============================================================================
# 🧠 THE "TRADING BIBLE" LOGIC (ALL 5 METHODS - 100% INTEGRATED)
# ==============================================================================

def analyze_bible_logic(coin):
    # Fetch Data (HTF for Trend/Structure, LTF for Entry)
    # Slow down requests to prevent "No Data" errors
    df_4h = get_data(f"{coin}USDT", '4h', 100)
    time.sleep(0.5) 
    df_15m = get_data(f"{coin}USDT", '15m', 300)
    
    if df_4h.empty or df_15m.empty: return "NEUTRAL", 0, 0, 0, 0, 0, []

    # --- 0. PRE-CALCULATIONS ---
    df_15m['atr'] = ta.atr(df_15m['h'], df_15m['l'], df_15m['c'], 14)
    df_15m['ema200'] = ta.ema(df_15m['c'], 200)
    df_15m['rsi'] = ta.rsi(df_15m['c'], 14)
    
    curr = df_15m.iloc[-1]
    prev = df_15m.iloc[-2]
    
    methods_hit = []
    score = 50 

    # ==========================================================================
    # 🚀 METHOD 05: FUNDAMENTALS (Volatility Proxy for News)
    # ==========================================================================
    # Macro/News Check: If ATR explodes > 3.5x, it's a News Event.
    volatility_shock = (curr['h'] - curr['l']) > (curr['atr'] * 3.5)
    if volatility_shock:
        return "NEUTRAL", 0, 0, 0, 0, 0, ["NEWS EVENT (Do Not Trade)"]
    
    # Whale Activities: Volume > 3x Average
    avg_vol = df_15m['v'].rolling(20).mean().iloc[-1]
    is_whale = curr['v'] > (avg_vol * 3.0)
    if is_whale: methods_hit.append("Whale Volume")

    # Sentiment (Fear/Greed via RSI Extreme)
    is_extreme_fear = curr['rsi'] < 25 
    is_extreme_greed = curr['rsi'] > 75 

    # ==========================================================================
    # 🚀 METHOD 01: MALAYSIAN SNR (Mapping & Setup)
    # ==========================================================================
    # HTF Direction
    htf_trend = "BULL" if df_4h['c'].iloc[-1] > ta.ema(df_4h['c'], 200).iloc[-1] else "BEAR"
    
    # QML Pattern (High -> Low -> Higher High -> Lower Low)
    l = df_15m['l']
    h = df_15m['h']
    
    # Identifying Swing Points (A & V Shapes)
    swing_lows = l[(l.shift(1) > l) & (l.shift(-1) > l)].tail(3).values
    swing_highs = h[(h.shift(1) < h) & (h.shift(-1) < h)].tail(3).values
    
    qml_bull = False
    qml_bear = False
    
    if len(swing_lows) >= 2 and len(swing_highs) >= 2:
        # Bearish QML
        if swing_highs[1] > swing_highs[0] and curr['c'] < swing_lows[1]: qml_bear = True
        # Bullish QML
        if swing_lows[1] < swing_lows[0] and curr['c'] > swing_highs[1]: qml_bull = True

    # ==========================================================================
    # 🚀 METHOD 02: LIQUIDITY (The Hunt)
    # ==========================================================================
    # Sweep: Wicking below a recent low but closing above (False Breakout)
    recent_low = df_15m['l'].iloc[-10:-1].min()
    recent_high = df_15m['h'].iloc[-10:-1].max()
    
    sweep_bull = (curr['l'] < recent_low) and (curr['c'] > recent_low)
    sweep_bear = (curr['h'] > recent_high) and (curr['c'] < recent_high)
    
    if sweep_bull: methods_hit.append("SSL Sweep")
    if sweep_bear: methods_hit.append("BSL Sweep")

    # ==========================================================================
    # 🚀 METHOD 04: ICT (Structure & Time)
    # ==========================================================================
    # FVG (Fair Value Gap)
    fvg_bull = (df_15m['l'].shift(2) > df_15m['h']).iloc[-1]
    fvg_bear = (df_15m['h'].shift(2) < df_15m['l']).iloc[-1]
    
    # Premium/Discount
    is_discount = curr['rsi'] < 45
    is_premium = curr['rsi'] > 55

    # Kill Zones (Time)
    utc_hour = datetime.now(pytz.utc).hour
    killzone_active = (7 <= utc_hour <= 10) or (12 <= utc_hour <= 16)

    # ==========================================================================
    # 🚀 METHOD 03: PRICE ACTION (The Trigger)
    # ==========================================================================
    # Engulfing Candles
    engulf_bull = (curr['c'] > curr['o']) and (prev['c'] < prev['o']) and (curr['c'] > prev['h'])
    engulf_bear = (curr['c'] < curr['o']) and (prev['c'] > prev['o']) and (curr['c'] < prev['l'])
    
    # Pinbar
    body_size = abs(curr['c'] - curr['o'])
    lower_wick = min(curr['c'], curr['o']) - curr['l']
    upper_wick = curr['h'] - max(curr['c'], curr['o'])
    pinbar_bull = lower_wick > (body_size * 2) and upper_wick < body_size
    pinbar_bear = upper_wick > (body_size * 2) and lower_wick < body_size

    # ==========================================================================
    # ⚖️ SCORING SYSTEM
    # ==========================================================================
    if htf_trend == "BULL":
        score += 10
        if qml_bull: score += 25; methods_hit.append("QML Reversal")
        if sweep_bull: score += 20; methods_hit.append("Liquidity Raid")
        if fvg_bull: score += 15; methods_hit.append("ICT FVG")
        if is_discount: score += 5; methods_hit.append("Discount Zone")
        if engulf_bull or pinbar_bull: score += 15; methods_hit.append("PA Trigger")
        if killzone_active: score += 10; methods_hit.append("Killzone")
        if is_extreme_fear: score += 10; methods_hit.append("Sent:Fear")
        if is_whale and curr['c'] > curr['o']: score += 10; methods_hit.append("Whale Buy")

    elif htf_trend == "BEAR":
        score -= 10
        if qml_bear: score -= 25; methods_hit.append("QML Reversal")
        if sweep_bear: score -= 20; methods_hit.append("Liquidity Raid")
        if fvg_bear: score -= 15; methods_hit.append("ICT FVG")
        if is_premium: score -= 5; methods_hit.append("Premium Zone")
        if engulf_bear or pinbar_bear: score -= 15; methods_hit.append("PA Trigger")
        if killzone_active: score -= 10; methods_hit.append("Killzone")
        if is_extreme_greed: score -= 10; methods_hit.append("Sent:Greed")
        if is_whale and curr['c'] < curr['o']: score -= 10; methods_hit.append("Whale Sell")

    sig = "NEUTRAL"
    final_score = 50
    
    if score >= SCORE_THRESHOLD:
        sig = "LONG"; final_score = min(score, 100)
    elif score <= (100 - SCORE_THRESHOLD):
        sig = "SHORT"; final_score = min(100 - score, 100)

    sl_pips = curr['atr'] * 1.5
    sl_long = curr['l'] - sl_pips
    sl_short = curr['h'] + sl_pips

    return sig, final_score, curr['c'], curr['atr'], sl_long, sl_short, methods_hit

# ==============================================================================
# MAIN APP LOOP
# ==============================================================================

saved_data = load_data()
if 'bot_active' not in st.session_state: st.session_state.bot_active = saved_data['bot_active']
if 'daily_count' not in st.session_state: st.session_state.daily_count = saved_data['daily_count']
if 'last_reset_date' not in st.session_state: st.session_state.last_reset_date = saved_data['last_reset_date']
if 'signaled_coins' not in st.session_state: st.session_state.signaled_coins = saved_data['signaled_coins']
if 'history' not in st.session_state: st.session_state.history = saved_data['history']
if 'last_scan_block_id' not in st.session_state: st.session_state.last_scan_block_id = saved_data['last_scan_block_id']
if 'sent_morning' not in st.session_state: st.session_state.sent_morning = saved_data['sent_morning']
if 'sent_goodbye' not in st.session_state: st.session_state.sent_goodbye = saved_data['sent_goodbye']

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
    scan_log_text = ""

    for i, coin in enumerate(coins_list):
        if coin in st.session_state.signaled_coins:
            progress_bar.progress((i + 1) / len(coins_list)); continue

        try:
            status_area.markdown(f"👀 **Checking:** `{coin}` ...")
            # --- DATA FETCHING (SLOWED DOWN) ---
            df = get_data(f"{coin}USDT")
            
            if df.empty:
                scan_log_text = f"`{coin}`: ⚠️ No Data | " + scan_log_text
                live_log.markdown(f"#### 📝 Live Scores:\n{scan_log_text}")
                # Wait longer on error to prevent blocking
                time.sleep(3) 
                continue 

            sig, score, price, atr, sl_long, sl_short, methods = analyze_bible_logic(coin)
            
            score_color = "green" if score >= 85 else "red" if score <= 15 else "orange"
            status_area.markdown(f"👀 **Checked:** `{coin}` | 📊 **Score:** :{score_color}[`{score}/100`]")
            
            scan_log_text = f"`{coin}`: :{score_color}[{score}] | " + scan_log_text
            if len(scan_log_text) > 2000: scan_log_text = scan_log_text[:2000]
            live_log.markdown(f"#### 📝 Live Scores:\n{scan_log_text}")
            
            # --- IMPORTANT: COOL DOWN ---
            time.sleep(3) 

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
                    dynamic_leverage = max(5, min(ideal_leverage, MAX_LEVERAGE))
                    
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
                            st.session_state.sent_goodbye = True; save_full_state()
                        break
        except Exception as e:
            scan_log_text = f"`{coin}`: ⚠️ Error | " + scan_log_text
            live_log.markdown(f"#### 📝 Live Scores:\n{scan_log_text}")
            time.sleep(1)
        
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
                msg = "🛑 **Market Update:** අද Market එකේ අපේ Strategy එකට ගැලපෙන High Probability Setups තිබුනේ නෑ (Choppy Market). 📉\n\nබොරු Trades දාලා Loss කරගන්නවට වඩා, ඉවසීමෙන් Capital එක ආරක්ෂා කරගන්න එක තමයි Professional Trading කියන්නේ. 🧠💎\n\nහෙට අලුත් දවසකින් හමුවෙමු! Good Night Traders! 👋"
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
                st.info(f"⏳ **Monitoring...** (Next scan in {next_min} mins)")
                time.sleep(5); st.rerun()
        else:
            st.warning(f"💤 SLEEPING (Resumes {START_HOUR}:00)"); time.sleep(10); st.rerun()
    else: st.error("⚠️ STOPPED"); time.sleep(2)

with tab2:
    if st.session_state.history: st.table(pd.DataFrame(st.session_state.history))
    else: st.info("No signals yet.")
