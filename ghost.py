import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime

# --- 1. USER SETTINGS (මෙතන ඔයාගේ විස්තර) ---
TELEGRAM_BOT_TOKEN = "8524773131:AAFuDVevQzNUwYeehLjQ3M-qK8QsmoaYK8c"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgIAAxkBAAEgGqpk7pKz" # Bull Sticker

# --- 2. DEFAULT BINANCE FUTURES LIST (සිකුරාදාට මේක වෙනස් කරන්න පුළුවන්) ---
DEFAULT_COINS = [
    "BTC", "ETH", "SOL", "BNB", "DOGE", "XRP", "ADA", "MATIC", "DOT", "LTC",
    "TRX", "AVAX", "LINK", "UNI", "ATOM", "NEAR", "ALGO", "FIL", "VET", "ICP",
    "SAND", "MANA", "AXS", "THETA", "AAVE", "EOS", "XTZ", "KLAY", "RUNE", "EGLD",
    "FTM", "CRV", "FLOW", "KAVA", "GALA", "HBAR", "MINA", "CHZ", "DYDX", "AR"
]

# --- 3. SETUP ---
st.set_page_config(page_title="Ghost Protocol VIP", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo') # ශ්‍රී ලංකා වෙලාව

# --- 4. FUNCTIONS ---
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
        # MEXC Data (Block වෙන්නේ නෑ)
        exchange = ccxt.mexc({'options': {'defaultType': 'swap'}})
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except: return pd.DataFrame()

# --- 5. KILLZONE STRATEGY (The Core Analysis) ---
def analyze(df):
    # Indicators
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    curr = df.iloc[-1]
    
    score = 50
    # 1. Trend Check (SMA 50)
    if curr['close'] > curr['sma50']: score += 15
    else: score -= 15
    
    # 2. Momentum Check (RSI)
    if curr['rsi'] < 30: score += 20
    elif curr['rsi'] > 70: score -= 20
    
    # Signal Decision
    sig = "NEUTRAL"
    if score >= 75: sig = "LONG"
    elif score <= 25: sig = "SHORT"
    
    return sig, score, curr['close'], curr['atr']

# --- 6. DASHBOARD & ENGINE ---
def main():
    st.title("👻 GHOST PROTOCOL : VIP ENGINE")
    
    # Session State Setup
    if 'coin_list' not in st.session_state:
        st.session_state.coin_list = ", ".join(DEFAULT_COINS)
    if 'signals_log' not in st.session_state:
        st.session_state.signals_log = []

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🎛️ Control Panel", "📝 Coin Manager", "📜 History"])

    with tab1:
        st.subheader("System Status")
        
        # Time Check (7 AM - 9 PM)
        now_lk = datetime.now(lz)
        hour = now_lk.hour
        is_active = 7 <= hour < 21 
        
        col_t1, col_t2 = st.columns(2)
        col_t1.metric("Sri Lanka Time", now_lk.strftime("%H:%M:%S"))
        
        if is_active:
            col_t2.success("✅ MARKET OPEN (Active Hours)")
        else:
            col_t2.error("💤 MARKET CLOSED (Sleep Mode)")

        st.markdown("---")
        
        # Buttons
        c1, c2 = st.columns(2)
        start = c1.button("🟢 START ENGINE")
        stop = c2.button("🔴 EMERGENCY STOP")
        
        status_box = st.empty()
        
        if stop:
            st.warning("🛑 Engine Stopped Manually.")
            st.stop()

        if start:
            if not is_active:
                st.error("⚠️ Can't start outside 7 AM - 9 PM window.")
            else:
                st.toast("Ghost Protocol Activated! 👻")
                coins = [x.strip() for x in st.session_state.coin_list.split(',')]
                
                while True:
                    # Loop එක ඇතුලේ වෙලාව චෙක් කිරීම
                    now_check = datetime.now(lz)
                    if not (7 <= now_check.hour < 21):
                        status_box.warning("💤 Time Up! Shutting down for the night...")
                        time.sleep(600)
                        continue

                    for coin in coins:
                        pair = f"{coin}/USDT:USDT"
                        status_box.text(f"Scanning {coin}...")
                        
                        df = get_data(pair)
                        if df.empty: continue
                        
                        sig, score, price, atr = analyze(df)
                        
                        # --- SIGNAL FOUND ---
                        if (sig == "LONG" and score >= 75) or (sig == "SHORT" and score <= 25):
                            
                            # 1. Sticker
                            send_telegram("Alert", sticker=True)
                            status_box.text(f"🔥 Signal Found on {coin}! Waiting 60s...")
                            time.sleep(60)
                            
                            # 2. Calc Targets (ATR Based)
                            sl_dist = atr * 1.5
                            if sig == "LONG":
                                sl = price - sl_dist
                                tps = [price + sl_dist*1.5, price + sl_dist*2.5, price + sl_dist*3.5]
                            else:
                                sl = price + sl_dist
                                tps = [price - sl_dist*1.5, price - sl_dist*2.5, price - sl_dist*3.5]
                            
                            rr = round(abs(tps[2]-price)/abs(price-sl), 2)
                            
                            # 3. Message
                            msg = f"""
💎 <b>CRYPTO CAMPUS VIP</b> 💎

🪙 <b>{coin} / USDT</b>
Signal: {sig} 🟢🔴

🟢 <b>Entry:</b> ${price:.4f}
🛡️ <b>StopLoss:</b> ${sl:.4f}

🎯 <b>Targets:</b>
1️⃣ ${tps[0]:.4f}
2️⃣ ${tps[1]:.4f}
3️⃣ ${tps[2]:.4f}

⚖️ <b>Risk/Reward:</b> 1:{rr}
👻 <i>Ghost System Analysis</i>
"""
                            send_telegram(msg)
                            
                            # Log History
                            log_entry = f"{now_check.strftime('%Y-%m-%d %H:%M')} | {coin} | {sig} | Entry: {price:.4f}"
                            st.session_state.signals_log.insert(0, log_entry)
                            
                            status_box.success(f"Signal Sent: {coin}")
                            time.sleep(900) # Cooldown 15 mins
                    
                    time.sleep(120) # 2 mins rest after full cycle

    with tab2:
        st.subheader("Manage Binance List")
        st.info("Edit this list on Fridays. Add new coins separated by commas.")
        txt = st.text_area("Active Coins", st.session_state.coin_list, height=300)
        if st.button("💾 Save List"):
            st.session_state.coin_list = txt
            st.success("Coin List Updated!")

    with tab3:
        st.subheader("Signal History")
        if st.session_state.signals_log:
            for item in st.session_state.signals_log:
                st.text(item)
        else:
            st.write("No signals generated yet today.")

if __name__ == "__main__":
    main()
