import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime

# --- 1. පෞද්ගලික තොරතුරු (ඔයා එවපු අලුත්ම Keys) ---
# ⚠️ මෙම Keys දෙක කිසිවෙකුට ලබා නොදෙන්න.
BINANCE_API_KEY = "FqcL7DzJDdHE9O40C3uqGbbR vABuDB5tcl3TdNumxlud2Sp893i tdtlloMiLAScW"
BINANCE_SECRET_KEY = "egshKJYbxZGvysWuEUmim5nml V5uYzCTYKS3GP94SjSMIFcL2SN mbOhQEUJNU85p"

TELEGRAM_BOT_TOKEN = "8524773131:AAFuDVevQzNUwYeehLjQ3M-qK8QsmoaYK8c"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWIMq--iOTVBE4BA"

# --- 2. SETUP & CONNECTION ---
st.set_page_config(page_title="Ghost Protocol: GOD MODE", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# Binance Futures සම්බන්ධතාවය (Block වීම් මගහැරීමට hostname ඇතුළත් කර ඇත)
exchange = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
    'hostname': 'fapi.binance.com',
    'adjustForTimeDifference': True
})

# --- 3. ANALYSIS ENGINE (SMC, RSI, ATR) ---
def analyze_market(symbol):
    try:
        # දත්ත ලබා ගැනීම
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # දර්ශක ගණනය කිරීම
        df['rsi'] = ta.rsi(df['close'], 14)
        df['sma50'] = ta.sma(df['close'], 50)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
        
        curr = df.iloc[-1]
        score = 50
        
        # Scoring Logic
        if curr['close'] > curr['sma50']: score += 20
        if curr['rsi'] < 35: score += 20
        if curr['volume'] > df['volume'].rolling(20).mean().iloc[-1] * 1.5: score += 10
        
        signal = "WAIT"
        if score >= 85: signal = "STRONG LONG 🚀"
        elif score <= 15: signal = "STRONG SHORT 📉"
        
        return signal, score, curr['close'], curr['atr']
    except:
        return None, 0, 0, 0

# --- 4. MAIN APP ---
def main():
    st.title("👻 GHOST PROTOCOL : GOD MODE ENGINE")
    
    # සම්බන්ධතාවය පරීක්ෂා කිරීම
    try:
        exchange.fetch_balance()
        st.success("System Status: ✅ Connected & Scanning Binance Futures")
    except Exception as e:
        st.error(f"System Status: ❌ Connection Error - API Keys හරියාකාරව ක්‍රියා නොකරයි හෝ Binance Block වී ඇත.")

    if 'active' not in st.session_state:
        st.session_state.active = True

    while st.session_state.active:
        now = datetime.now(lz)
        # කාල නීතිය: උදේ 7 - රෑ 9
        if 7 <= now.hour < 21:
            try:
                markets = exchange.load_markets()
                symbols = [s for s in markets if '/USDT' in s]
                
                for symbol in symbols[:20]: # මුල් කොයින් 20 පරීක්ෂා කරයි
                    sig, score, price, atr = analyze_market(symbol)
                    if sig != "WAIT":
                        # Telegram පණිවිඩය යැවීම
                        msg = f"<b>🔥 GOD MODE: {symbol}</b>\n\nSide: {sig}\nScore: {score}%\nPrice: {price}\nSL: {price - (atr*2):.4f}"
                        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
                        requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
                        requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
            except:
                pass
            time.sleep(900) # විනාඩි 15කට වරක්
        else:
            st.info("🌙 Night Mode (Scanning Paused)")
            time.sleep(60)

if __name__ == "__main__":
    main()
