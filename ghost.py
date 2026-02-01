import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime

# --- 1. පෞද්ගලික තොරතුරු (හිස්තැන් ඉවත් කළ Keys) ---
BINANCE_API_KEY = "FqcL7DzJDdHE9O40C3uqGbbRvABuDB5tcl3TdNumxlud2Sp893itdtlloMiLAScW"
BINANCE_SECRET_KEY = "egshKJYbxZGvysWuEUmim5nmlV5uYzCTYKS3GP94SjSMIFcL2SNmbOhQEUJNU85p"

TELEGRAM_BOT_TOKEN = "8524773131:AAFuDVevQzNUwYeehLjQ3M-qK8QsmoaYK8c"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWIMq--iOTVBE4BA"

# --- 2. SETUP ---
st.set_page_config(page_title="Ghost Protocol: GOD MODE", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# Binance Futures සම්බන්ධතාවය
exchange = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
    'hostname': 'fapi.binance.com', # Block වීම් මගහැරීමට
    'adjustForTimeDifference': True
})

# --- 3. ANALYSIS ENGINE ---
def analyze_market(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['rsi'] = ta.rsi(df['close'], 14)
        df['sma50'] = ta.sma(df['close'], 50)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
        
        curr = df.iloc[-1]
        score = 50
        
        if curr['close'] > curr['sma50']: score += 20
        if curr['rsi'] < 35: score += 20
        
        signal = "WAIT"
        if score >= 85: signal = "STRONG LONG 🚀"
        elif score <= 15: signal = "STRONG SHORT 📉"
        
        return signal, score, curr['close'], curr['atr']
    except: return None, 0, 0, 0

# --- 4. MAIN APP ---
def main():
    st.title("👻 GHOST PROTOCOL : GOD MODE ENGINE")
    
    try:
        exchange.fetch_balance()
        st.success("System Status: ✅ Connected & Scanning Binance Futures")
    except Exception as e:
        st.error(f"System Status: ❌ Connection Error - Keys නිවැරදිව පරීක්ෂා කරන්න.")

    if 'active' not in st.session_state: st.session_state.active = True

    while st.session_state.active:
        now = datetime.now(lz)
        # කාල නීතිය: උදේ 7 - රෑ 9
        if 7 <= now.hour < 21:
            try:
                markets = exchange.load_markets()
                symbols = [s for s in markets if '/USDT' in s]
                for symbol in symbols[:15]: 
                    sig, score, price, atr = analyze_market(symbol)
                    if sig != "WAIT":
                        msg = f"<b>🔥 GOD MODE: {symbol}</b>\n\nSide: {sig}\nScore: {score}%\nPrice: {price}\nSL: {price - (atr*2):.4f}"
                        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
                        requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
                        requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
            except: pass
            time.sleep(900)
        else:
            st.info("🌙 Night Mode (Scanning Paused)")
            time.sleep(60)

if __name__ == "__main__":
    main()
