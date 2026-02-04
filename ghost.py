import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
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
SCORE_THRESHOLD = 80  

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
                today_str = datetime.now(lz).strftime("%Y-%m-%d")
                
                if data.get("last_reset_date") != today_str:
                    data["daily_count"] = 0
                    data["signaled_coins"] = []
                    data["last_reset_date"] = today_str
                    data["sent_morning"] = False
                    data["sent_goodbye"] = False
                
                if "sent_morning" not in data: data["sent_morning"] = False
                if "sent_goodbye" not in data: data["sent_goodbye"] = False
                
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

# --- OPTIMIZED EXCHANGE CONNECTION ---
@st.cache_resource
def get_exchange():
    return ccxt.mexc({
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True  # FIX: Prevents getting blocked by MEXC
    })

def get_data(symbol, limit=200, timeframe='15m'):
    exchange = get_exchange()
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except: 
        return pd.DataFrame()

# --- METHOD 13: TIME ANALYSIS (SESSION KILLZONES) ---
def get_time_analysis():
    now = datetime.now(lz)
    hour = now.hour
    if 12 <= hour <= 22: return "HIGH_VOLUME", 10 
    elif 2 <= hour <= 6: return "DEAD_ZONE", -50 
    else: return "NEUTRAL", 0

# --- METHOD 9: NEWS IMPACT CHECK ---
def check_news_impact(btc_df):
    if btc_df.empty: return False
    curr = btc_df.iloc[-1]
    change = abs(curr['close'] - curr['open']) / curr['open'] * 100
    if change > 1.5: return True # SHOCK DETECTED
    return False

# --- THE 13 METHOD ANALYZER (GHOST ENGINE 2.0 - PRO) ---
def analyze_ultimate(df, coin_name):
    if df.empty or len(df) < 200: return "NEUTRAL", 0, 0, 0, 0, 0, []
    
    # --- SAFETY 1: FETCH HIGHER TIMEFRAMES ---
    try:
        # Fetching higher timeframes might fail due to rate limits, handle gracefully
        df_4h = get_data(f"{coin_name}/USDT:USDT", limit=50, timeframe='4h')
        if not df_4h.empty:
            df_4h['ema200'] = ta.ema(df_4h['close'], 200)
            trend_4h = "BULLISH" if df_4h.iloc[-1]['close'] > df_4h.iloc[-1].get('ema200', 0) else "BEARISH"
        else: trend_4h = "NEUTRAL"
        
        df_daily = get_data(f"{coin_name}/USDT:USDT", limit=5, timeframe='1d')
        if not df_daily.empty:
            prev_day = df_daily.iloc[-2] 
            prev_day_low = prev_day['low']
            prev_day_high = prev_day['high']
        else:
            prev_day_low = 0; prev_day_high = 9999999
    except:
        trend_4h = "NEUTRAL"; prev_day_low = 0; prev_day_high = 9999999

    # --- INDICATORS ---
    df['rsi'] = ta.rsi(df['close'], 14)
    df['stoch_k'] = ta.stochrsi(df['close'], length=14, k=3, d=3)['STOCHRSIk_14_14_3_3']
    df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
    df['ema200'] = ta.ema(df['close'], 200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    
    macd = ta.macd(df['close'])
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    
    bb = ta.bbands(df['close'], length=20)
    df['bb_upper'] = bb['BBU_20_2.0']
    df['bb_lower'] = bb['BBL_20_2.0']
    df['bb_width'] = bb['BBB_20_2.0']

    curr = df.iloc[-1]; prev = df.iloc[-2]
    score = 50; methods_hit = []
    
    # --- SAFETY 2: FLASH CRASH SHIELD ---
    candle_size = abs(curr['high'] - curr['low'])
    if candle_size > (curr['atr'] * 3): 
        return "NEUTRAL", 0, 0, 0, 0, 0, ["VOLATILITY SPIKE"]

    # --- METHOD 13: Time Analysis ---
    time_status, time_score = get_time_analysis()
    score += time_score
    if time_status == "DEAD_ZONE": return "NEUTRAL", 0, 0, 0, 0, 0, ["DEAD ZONE"]

    # --- METHOD 2: ADX Filter ---
    if curr['adx'] < 20: return "NEUTRAL", 0, 0, 0, 0, 0, ["LOW ADX (CHOP)"]
        
    # --- METHOD 1 + SAFETY 1: Trend ---
    is_15m_bull = curr['close'] > curr['ema200']
    is_15m_bear = curr['close'] < curr['ema200']
    structure_broken_down = curr['close'] < prev_day_low
    structure_broken_up = curr['close'] > prev_day_high

    if trend_4h == "BULLISH" and is_15m_bull: 
        if not structure_broken_down: score += 15
        else: score -= 50 
        
    if trend_4h == "BEARISH" and is_15m_bear: 
        if not structure_broken_up: score -= 15
        else: score += 50 

    # --- METHOD 3: Volume ---
    vol_ma = df['volume'].rolling(20).mean().iloc[-1]
    if curr['volume'] > vol_ma:
        if curr['close'] > curr['open']: score += 5 
        else: score -= 5 
    else:
        if abs(curr['close'] - curr['open']) > curr['atr']: score = 50 

    # --- METHOD 4: Sniper Entry ---
    stoch_buy = curr['stoch_k'] < 20 and curr['stoch_k'] > prev['stoch_k']
    stoch_sell = curr['stoch_k'] > 80 and curr['stoch_k'] < prev['stoch_k']
    macd_buy = curr['macd'] > curr['macd_signal']
    macd_sell = curr['macd'] < curr['macd_signal']
    
    if stoch_buy and macd_buy: score += 15; methods_hit.append("Sniper Buy")
    if stoch_sell and macd_sell: score -= 15; methods_hit.append("Sniper Sell")

    # --- METHOD 5: MSNR ---
    res = df['high'].iloc[-50:].max(); sup = df['low'].iloc[-50:].min()
    if abs(curr['close'] - sup) < (curr['atr'] * 0.5): score += 10; methods_hit.append("Support Bounce")
    if abs(curr['close'] - res) < (curr['atr'] * 0.5): score -= 10; methods_hit.append("Resistance Reject")

    # --- METHOD 6: Liquidity Grab ---
    local_low = df['low'].iloc[-10:-1].min()
    if prev['low'] < local_low and curr['close'] > prev['high']:
        score += 15; methods_hit.append("Liquidity Grab Buy")

    # --- METHOD 7: Price Action ---
    if prev['close'] < prev['open'] and curr['close'] > curr['open'] and curr['close'] > prev['open']:
        score += 10; methods_hit.append("Bullish Engulfing")
    
    # --- METHOD 8: ICT (FVG) ---
    if df.iloc[-3]['high'] < df.iloc[-1]['low']: score += 10; methods_hit.append("FVG Support")
    
    # --- METHOD 10: Fib ---
    if 40 < curr['rsi'] < 60 and trend_4h == "BULLISH": score += 5; methods_hit.append("Fib Pullback")

    # --- METHOD 11: RSI Div ---
    if curr['close'] < df['close'].iloc[-5] and curr['rsi'] > df['rsi'].iloc[-5]:
        score += 15; methods_hit.append("RSI Divergence")

    # --- METHOD 12: BB Squeeze ---
    if curr['bb_width'] < df['bb_width'].mean() * 0.8:
        if curr['close'] > curr['bb_upper']: score += 15; methods_hit.append("BB Breakout Buy")
        elif curr['close'] < curr['bb_lower']: score -= 15; methods_hit.append("BB Breakout Sell")

    # --- SAFETY 4: ATR BUFFER ---
    swing_low = df['low'].iloc[-15:].min()  
    swing_high = df['high'].iloc[-15:].max()
    atr_buffer = curr['atr'] * 0.5
    sl_long = swing_low - atr_buffer
    sl_short = swing_high + atr_buffer

    sig = "LONG" if score >= SCORE_THRESHOLD else "SHORT" if score <= (100 - SCORE_THRESHOLD) else "NEUTRAL"
    return sig, score, curr['close'], curr['atr'], sl_long, sl_short, methods_hit

# --- SESSION STATE ---
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
        btc_df = get_data("BTC/USDT:USDT", limit=50)
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
            
            df = get_data(f"{coin}/USDT:USDT")
            
            if df.empty:
                # FIX: Show error if data fetching failed
                status_area.markdown(f"⚠️ **Error:** `{coin}` | ❌ No Data (Retrying...)")
                time.sleep(0.5)
                continue # Skip to next coin

            sig, score, price, atr, sl_long, sl_short, methods = analyze_ultimate(df, coin)
            
            score_color = "green" if score > 80 else "orange" if score > 50 else "red"
            
            # Show Score
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

        except: pass
        progress_bar.progress((i + 1) / len(coins_list))
    
    status_area.empty(); st.success("Scan Complete!"); return

with tab1:
    if st.session_state.bot_active:
        if is_within_hours and not st.session_state.sent_morning:
            send_telegram("☀️ Good Morning Traders! ඔයාලා හැමෝටම ජයග්‍රාහී සුබ දවසක් වේවා! 🚀")
            st.session_state.sent_morning = True
            save_full_state()

        # --- SMART GOODBYE LOGIC ---
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
