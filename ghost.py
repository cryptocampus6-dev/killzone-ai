import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime, timedelta

# --- USER SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAFuDVevQzNUwYeehLjQ3M-qK8QsmoaYK8c"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWIMq--iOTVBE4BA"

# ස්ථිර Coin List එක (මෙතන වෙනස් කළාම කවදාවත් මැකෙන්නේ නෑ)
FIXED_COINS = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", 
    "NEAR", "MATIC", "PEPE", "SUI", "RENDER", "WIF", "BONK", "FET", "AR", "INJ"
]

st.set_page_config(page_title="Ghost Protocol VIP", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

def send_telegram(msg, is_sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if is_sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else:
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
        return True
    except: return False

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

def main():
    st.title("👻 GHOST PROTOCOL : FINAL EDITION")
    
    # Sidebar Test Button
    st.sidebar.header("🛠️ Diagnostics")
    if st.sidebar.button("Test Telegram Connection 📡"):
        res = send_telegram("🔔 <b>Test Message:</b> Ghost Protocol is Connected!", is_sticker=False)
        if res: st.sidebar.success("Message Sent Successfully!")
        else: st.sidebar.error("Failed to send message.")

    if 'signals_log' not in st.session_state:
        st.session_state.signals_log = []

    # Status Display
    now_live = datetime.now(lz)
    st.metric("System Time (LK) 🇱🇰", now_live.strftime("%H:%M:%S"))
    st.success("✅ SYSTEM ACTIVE - Scanning Market...")

    # Scanning Logic
    coins = FIXED_COINS
    
    # Auto-Run Logic (Runs every loop)
    placeholder = st.empty()
    
    # Loop එකක් දාලා තියෙන්නේ Page එක Refresh නොවුණත් දිගටම යන්න
    for i in range(1000):
        current_time = datetime.now(lz)
        
        # විනාඩි 15කට වරක් ස්කෑන් කිරීම
        if current_time.minute % 15 == 0 and current_time.second < 30:
            placeholder.markdown(f"**🔄 Scanning {len(coins)} Coins...**")
            
            for coin in coins:
                try:
                    df = get_data(f"{coin}/USDT:USDT")
                    if not df.empty:
                        sig, score, price, atr = analyze(df)
                        if sig != "NEUTRAL":
                            send_telegram("", is_sticker=True)
                            
                            sl_dist = atr * 1.5
                            tp_dist = sl_dist
                            if sig == "LONG":
                                sl = price - sl_dist
                                tps = [price + tp_dist*x for x in range(1, 5)]
                            else:
                                sl = price + sl_dist
                                tps = [price - tp_dist*x for x in range(1, 5)]
                            
                            rr = round(abs(tps[3]-price)/abs(price-sl), 2)
                            
                            msg = (f"💎 <b>VIP SIGNAL</b>\n\n"
                                   f"🪙 <b>{coin}/USDT</b>\n"
                                   f"Direction: <b>{sig}</b>\n"
                                   f"Entry: {price:.4f}\n"
                                   f"Targets: {tps[0]:.4f} | {tps[1]:.4f} | {tps[2]:.4f}\n"
                                   f"Stop Loss: {sl:.4f}\n"
                                   f"RR: 1:{rr}")
                            
                            send_telegram(msg)
                            log_msg = f"{current_time.strftime('%H:%M')} | {coin} | {sig}"
                            st.session_state.signals_log.insert(0, log_msg)
                except: pass
            
            time.sleep(60) # විනාඩියක් ඉන්න ඊළඟ වටේට කලින්
            st.rerun() # Refresh app to update logs
        
        time.sleep(1) # CPU එක load නොවී තියාගන්න

    st.subheader("📜 Signal History")
    for item in st.session_state.signals_log: st.text(item)

if __name__ == "__main__":
    main()
