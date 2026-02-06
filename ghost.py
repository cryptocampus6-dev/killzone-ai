import streamlit as st
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
import os
import json
import numpy as np
from datetime import datetime, timedelta

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
                today_str = datetime.now(lz).strftime("%Y-%m-%d")
                if data.get("last_reset_date") != today_str:
                    data["daily_count"] = 0
                    data["signaled_coins"] = []
                    data["last_reset_date"] = today_str
                    data["sent_morning"] = False
                    data["sent_goodbye"] = False
                return data
        except: return default_data
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

# --- ROBUST DATA FETCHING (FIXED WITH HEADERS) ---
def get_data(symbol, limit=200, timeframe='15m'):
    # Uses MEXC Spot API with Browser Headers to avoid blocking
    try:
        url = "https://api.mexc.com/api/v3/klines"
        params = {
            'symbol': symbol, 
            'interval': timeframe,
            'limit': limit
        }
        # 🔑 KEY FIX: User-Agent Header mimics a real browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Log specific error code if not 200
        if response.status_code != 200:
            return pd.DataFrame(), f"Status: {response.status_code}"

        data = response.json()

        if isinstance(data, dict) and "code" in data:
            return pd.DataFrame(), f"API Error: {data['msg']}"

        if not isinstance(data, list):
            return pd.DataFrame(), "Invalid Data Format"

        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'c_time', 'qav', 'num', 'tbv', 'tqv', 'ign'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        cols = ['open', 'high', 'low', 'close', 'volume']
        df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
        
        return df, "OK"
        
    except Exception as e:
        return pd.DataFrame(), str(e)

# ==============================================================================
# 🧠 100% IMPLEMENTATION OF "THE TRADING BIBLE"
# ==============================================================================

# --- 1. MALAYSIAN SNR (FULL SUITE) ---
def analyze_msnr(df):
    df['swing_high'] = df['high'][(df['high'].shift(1) < df['high']) & (df['high'].shift(-1) < df['high'])]
    df['swing_low'] = df['low'][(df['low'].shift(1) > df['low']) & (df['low'].shift(-1) > df['low'])]
    
    last_highs = df['swing_high'].dropna().tail(3).values
    last_lows = df['swing_low'].dropna().tail(3).values
    
    qml_bullish = False; qml_bearish = False; fresh_level = True; compression = False

    if len(last_highs) >= 2 and len(last_lows) >= 2:
        if last_highs[1] > last_highs[0] and df['close'].iloc[-1] < last_lows[1]: qml_bearish = True
        if last_lows[1] < last_lows[0] and df['close'].iloc[-1] > last_highs[1]: qml_bullish = True

    avg_body = abs(df['open'] - df['close']).mean()
    last_3_bodies = abs(df['open'].tail(3) - df['close'].tail(3)).mean()
    if last_3_bodies < avg_body * 0.7: compression = True

    return qml_bullish, qml_bearish, fresh_level, compression

# --- 2. ICT (FULL SUITE) ---
def analyze_ict(df):
    bullish_fvg = (df['low'].shift(2) > df['high']) 
    bearish_fvg = (df['high'].shift(2) < df['low'])
    
    prev_high = df['high'].rolling(10).max().shift(1)
    sweep_high = (df['high'] > prev_high) & (df['close'] < prev_high)
    prev_low = df['low'].rolling(10).min().shift(1)
    sweep_low = (df['low'] < prev_low) & (df['close'] > prev_low)

    bearish_ob = (df['close'].shift(1) > df['open'].shift(1)) and (df['close'] < df['open']) and (df['close'] < df['low'].shift(1))
    bullish_ob = (df['close'].shift(1) < df['open'].shift(1)) and (df['close'] > df['open']) and (df['close'] > df['
