import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime, timedelta

# --- USER SETTINGS (ඔයාගේ අලුත් Token එක මෙතනට දැම්මා) ---
TELEGRAM_BOT_TOKEN = "8524773131:AAE-ByPKx7x0ClDOLEQg1aw8j0tWYb41_CY"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWIMq--iOTVBE4BA"

# ස්ථිර Coin List එක
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
            response = requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else:
            response = requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
        return response.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

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
    
    # Sidebar Test Button with Debugger
    st.sidebar.header("🛠️ Diagnostics")
    if st.sidebar.button("Test Telegram Connection 📡"):
        res = send_telegram("🔔 <b>Test Message:</b> Ghost Protocol is Connected! 🚀", is_sticker=False)
        st.sidebar.json(res) 
        if res.get("ok"):
            st.sidebar.success("Message Sent Successfully! ✅")
        else:
            st.sidebar.error(f"Failed! Error: {res.get('description')}")

    if 'signals_log' not in st.session_state:
        st.session_state.signals_log = []

    # Status Display
    now_live = datetime.now(lz)
    st.metric("System Time (LK) 🇱🇰", now_live.strftime("%H:%M:%S"))
    st.success("✅ SYSTEM ACTIVE - Scanning Market...")

    coins = FIXED_COINS
    placeholder = st.empty()
    
    # Main Loop
    for i in range(1000):
        current_time = datetime.now(lz)
        
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
            
            time.sleep(60)
            st.rerun()
        
        time.sleep(1)

    st.subheader("📜 Signal History")
    for item in st.session_state.signals_log: st.text(item)

if __name__ == "__main__":
    main()
