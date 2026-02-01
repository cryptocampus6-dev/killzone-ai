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
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWIMq--iOTVBE4BA"

# Default Coin List (ඔයාට මේක මැනේජර් එකෙන් වෙනස් කරන්න පුළුවන්)
DEFAULT_COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", "NEAR", "MATIC", "PEPE", "SUI", "RENDER"]

# --- 2. SETUP ---
st.set_page_config(page_title="Ghost Protocol VIP", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- 3. FUNCTIONS ---
def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else:
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

def get_data(symbol):
    try:
        exchange = ccxt.mexc({'options': {'defaultType': 'swap'}})
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        return pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
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
    sig = "LONG" if score >= 75 else "SHORT" if score <= 25 else "NEUTRAL"
    return sig, score, curr['close'], curr['atr']

# --- 4. MAIN ENGINE ---
def main():
    st.title("👻 GHOST PROTOCOL : VIP ENGINE")
    
    # Session State Initialization
    if 'coin_list' not in st.session_state:
        st.session_state.coin_list = ", ".join(DEFAULT_COINS)
    if 'signals_log' not in st.session_state:
        st.session_state.signals_log = []
    if 'engine_running' not in st.session_state:
        st.session_state.engine_running = True

    tab1, tab2, tab3 = st.tabs(["🎛️ Control Panel", "📝 Coin Manager", "📜 History"])

    with tab1:
        time_placeholder = st.empty()
        status_placeholder = st.empty()
        log_box = st.empty()
        
        if st.session_state.engine_running:
            coins = [x.strip() for x in st.session_state.coin_list.split(',') if x.strip()]
            last_scan_time = datetime.now(lz) - timedelta(minutes=16)

            while st.session_state.engine_running:
                now_live = datetime.now(lz)
                time_placeholder.metric("Sri Lanka Time 🇱🇰", now_live.strftime("%H:%M:%S"))
                status_placeholder.success("✅ ENGINE RUNNING (24/7 ACTIVE)")

                time_diff = (now_live - last_scan_time).total_seconds()
                if time_diff >= 900: # 15 Mins
                    log_box.markdown(f"**🔄 Scanning {len(coins)} Coins...**")
                    for coin in coins:
                        try:
                            df = get_data(f"{coin}/USDT:USDT")
                            if not df.empty:
                                sig, score, price, atr = analyze(df)
                                if sig != "NEUTRAL":
                                    # ස්ටිකර් එක මුලින්ම යවනවා
                                    send_telegram("", is_sticker=True)
                                    
                                    # Target ගණනය කිරීම
                                    sl_dist = atr * 1.5
                                    lev = 20 # Default Leverage
                                    if sig == "LONG":
                                        sl = price - sl_dist
                                        tp1, tp2, tp3, tp4 = price + sl_dist, price + sl_dist*2, price + sl_dist*3, price + sl_dist*4
                                    else:
                                        sl = price + sl_dist
                                        tp1, tp2, tp3, tp4 = price - sl_dist, price - sl_dist*2, price - sl_dist*3, price - sl_dist*4
                                    
                                    rr = round(abs(tp4-price)/abs(price-sl), 2)
                                    
                                    # අවිශ්ක ඉල්ලපු විදිහටම පණිවිඩය
                                    msg = (f"💎 <b>VIP SIGNAL</b>\n\n"
                                           f"🪙 <b>{coin}/USDT</b>\n\n"
                                           f"Direction: <b>{sig}</b>\n"
                                           f"Leverage: Cross {lev}x\n\n"
                                           f"Entry: {price:.4f}\n\n"
                                           f"<b>Take Profit:</b>\n"
                                           f"1. {tp1:.4f} (25%)\n"
                                           f"2. {tp2:.4f} (50%)\n"
                                           f"3. {tp3:.4f} (75%)\n"
                                           f"4. {tp4:.4f} (100%)\n\n"
                                           f"Stop Loss: {sl:.4f}\n\n"
                                           f"<b>Margin Use: 1%-3%</b>\n"
                                           f"RR: 1:{rr}")
                                    
                                    send_telegram(msg)
                                    st.session_state.signals_log.insert(0, f"{now_live.strftime('%H:%M')} | {coin} | {sig}")
                        except: pass
                    last_scan_time = now_live
                time.sleep(1)

    with tab2:
        st.subheader("📝 Coin Manager")
        # මෙතන තමයි කොයින් ලිස්ට් එක පේන්නේ
        new_list = st.text_area("Edit Coin List (Separate with commas)", value=st.session_state.coin_list, height=300)
        if st.button("Update List"):
            st.session_state.coin_list = new_list
            st.success("Coin List Updated Successfully!")
            st.rerun()

    with tab3:
        st.subheader("📜 History")
        for item in st.session_state.signals_log: st.text(item)

if __name__ == "__main__":
    main()
