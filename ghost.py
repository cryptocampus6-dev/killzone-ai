import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime, timedelta

# --- 1. USER SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAFuDVevQzNUwYeehLjQ3M-qK8QsmoaYK8c"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgIAAxkBAAEgGqpk7pKz"

# Default List
DEFAULT_COINS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "XRP", "ADA", "MATIC", "DOT", "LTC",
    "TRX", "AVAX", "LINK", "UNI", "ATOM", "NEAR", "ALGO", "FIL", "VET", "ICP",
    "SAND", "MANA", "AXS", "THETA", "AAVE", "EOS", "XTZ", "KLAY", "RUNE", "EGLD"
]

# --- 2. SETUP ---
st.set_page_config(page_title="Ghost Protocol VIP", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- 3. FUNCTIONS ---
def send_telegram(msg, sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else:
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

def get_data(symbol):
    try:
        exchange = ccxt.mexc({'options': {'defaultType': 'swap'}})
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except: return pd.DataFrame()

def analyze(df):
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    curr = df.iloc[-1]
    
    score = 50
    if curr['close'] > curr['sma50']: score += 15
    else: score -= 15
    if curr['rsi'] < 30: score += 20
    elif curr['rsi'] > 70: score -= 20
    
    sig = "NEUTRAL"
    if score >= 75: sig = "LONG"
    elif score <= 25: sig = "SHORT"
    return sig, score, curr['close'], curr['atr']

# --- 4. MAIN ENGINE ---
def main():
    st.title("👻 GHOST PROTOCOL : VIP ENGINE")
    
    if 'coin_list' not in st.session_state:
        st.session_state.coin_list = ", ".join(DEFAULT_COINS)
    if 'signals_log' not in st.session_state:
        st.session_state.signals_log = []

    tab1, tab2, tab3 = st.tabs(["🎛️ Control Panel", "📝 Coin Manager", "📜 History"])

    with tab1:
        # Time Display Placeholder (මේක පස්සේ ලයිව් අප්ඩේට් වෙනවා)
        time_display = st.empty()
        status_display = st.empty()
        
        # Initial Time Show
        now_lk = datetime.now(lz)
        time_display.metric("Sri Lanka Time", now_lk.strftime("%H:%M:%S"))
        
        if 7 <= now_lk.hour < 21:
            status_display.success("✅ MARKET OPEN (Active Hours)")
        else:
            status_display.error("💤 MARKET CLOSED (Sleep Mode)")

        st.markdown("---")
        
        c1, c2 = st.columns(2)
        start = c1.button("🟢 START ENGINE")
        stop = c2.button("🔴 EMERGENCY STOP")
        
        # Output Area
        log_box = st.empty()
        
        if stop:
            st.warning("🛑 Engine Stopped.")
            st.stop()

        if start:
            st.toast("Engine Started! Time is now LIVE ⏱️")
            coins = [x.strip() for x in st.session_state.coin_list.split(',')]
            
            # Loop Setup
            last_scan_time = datetime.now(lz) - timedelta(minutes=15) # Force first scan
            
            while True:
                # 1. LIVE CLOCK UPDATE (තත්පරෙන් තත්පරේට)
                now_live = datetime.now(lz)
                time_display.metric("Sri Lanka Time 🇱🇰", now_live.strftime("%H:%M:%S"))
                
                # Check Market Hours
                if not (7 <= now_live.hour < 21):
                    status_display.error("💤 Sleeping... (Waiting for 7 AM)")
                    log_box.info("Night Mode Active 🌙")
                    time.sleep(60)
                    continue
                else:
                    status_display.success("✅ ENGINE RUNNING (Live)")

                # 2. SCANNING LOGIC (විනාඩි 15කට සැරයක්)
                time_diff = (now_live - last_scan_time).total_seconds()
                
                if time_diff >= 900: # 900 seconds = 15 Mins
                    log_box.markdown(f"**🔄 Scanning Market... ({len(coins)} Coins)**")
                    
                    for coin in coins:
                        try:
                            df = get_data(f"{coin}/USDT:USDT")
                            if df.empty: continue
                            
                            sig, score, price, atr = analyze(df)
                            
                            if (sig == "LONG" and score >= 75) or (sig == "SHORT" and score <= 25):
                                # Signal Logic
                                send_telegram("Alert", sticker=True)
                                sl_dist = atr * 1.5
                                if sig == "LONG":
                                    sl = price - sl_dist
                                    tps = [price + sl_dist*1.5, price + sl_dist*2.5, price + sl_dist*3.5]
                                else:
                                    sl = price + sl_dist
                                    tps = [price - sl_dist*1.5, price - sl_dist*2.5, price - sl_dist*3.5]
                                
                                rr = round(abs(tps[2]-price)/abs(price-sl), 2)
                                msg = f"💎 <b>VIP SIGNAL</b>\n\n🪙 <b>{coin}</b>\nSignal: {sig}\nEntry: {price:.4f}\nTargets: {tps[0]:.4f} | {tps[1]:.4f} | {tps[2]:.4f}\nSL: {sl:.4f}"
                                send_telegram(msg)
                                
                                log_entry = f"{now_live.strftime('%H:%M')} | {coin} | {sig}"
                                st.session_state.signals_log.insert(0, log_entry)
                        except: continue
                    
                    last_scan_time = now_live
                    log_box.success(f"✅ Scan Complete at {now_live.strftime('%H:%M:%S')}. Waiting for next cycle...")
                
                else:
                    # Waiting Message (Countdown)
                    mins_left = int((900 - time_diff) / 60)
                    log_box.info(f"⏳ Next Scan in {mins_left} minutes...")
                
                # 3. Small Sleep (To prevent crashing)
                time.sleep(1) # Update clock every second

    with tab2:
        st.subheader("Coin Manager")
        txt = st.text_area("Active Coins", st.session_state.coin_list, height=300)
        if st.button("Save List"): st.session_state.coin_list = txt

    with tab3:
        st.subheader("History")
        for item in st.session_state.signals_log: st.text(item)

if __name__ == "__main__":
    main()
