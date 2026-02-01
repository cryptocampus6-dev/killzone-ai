import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import time
import os

# --- 1. PAGE CONFIGURATION & BRANDING (MUST BE FIRST) ---
st.set_page_config(
    page_title="KillZone Pro Trading",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #eaecef; font-family: sans-serif; }
    [data-testid="stSidebar"] { background-color: #1e2329; border-right: 1px solid #2b3139; }
    
    /* CLASSIC SIGNAL BOX */
    .signal-box { background-color: #1e2329; border: 1px solid #2b3139; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .sig-header { color: #FCD535; font-size: 20px; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #444; padding-bottom: 10px; }
    .sig-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 15px; }
    .sig-label { color: #848e9c; }
    .sig-val { color: #fff; font-weight: bold; font-family: monospace; }
    .sig-roi { font-size: 12px; margin-left: 5px; opacity: 0.8; }
    .sig-long { color: #0ECB81; }
    .sig-short { color: #F6465D; }
    .sig-lev { background-color: #333; color: #FCD535; padding: 2px 5px; border-radius: 3px; }
    
    /* STRATEGY TAGS */
    .strategy-tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #333; color: #aaa; margin-right: 5px; border: 1px solid #444; display: inline-block; margin-bottom: 2px; }
    
    /* HOT COINS */
    .hot-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; font-size: 13px; }
    .hot-up { color: #0ECB81; }
    .hot-down { color: #F6465D; }
    .title-text { font-size: 35px; font-weight: bold; color: #ffffff; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. EXCHANGE CONNECTION (MEXC) ---
try:
    exchange = ccxt.mexc({
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
except:
    exchange = ccxt.binanceus({'options': {'defaultType': 'spot'}})

# --- 4. DATA FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_symbols():
    try:
        mkts = exchange.load_markets(reload=True)
        symbols = [s for s in mkts if "/USDT" in s]
        return symbols
    except: return ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "AI/USDT:USDT"]

@st.cache_data(ttl=60)
def get_hot_coins():
    try:
        tickers = exchange.fetch_tickers()
        usdt_tickers = {k: v for k, v in tickers.items() if '/USDT' in k}
        sorted_t = sorted(usdt_tickers.items(), key=lambda x: float(import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import time
import os

# --- 1. PAGE CONFIGURATION & BRANDING (MUST BE FIRST) ---
st.set_page_config(
    page_title="KillZone Pro Trading",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #eaecef; font-family: sans-serif; }
    [data-testid="stSidebar"] { background-color: #1e2329; border-right: 1px solid #2b3139; }
    
    /* CLASSIC SIGNAL BOX */
    .signal-box { background-color: #1e2329; border: 1px solid #2b3139; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .sig-header { color: #FCD535; font-size: 20px; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #444; padding-bottom: 10px; }
    .sig-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 15px; }
    .sig-label { color: #848e9c; }
    .sig-val { color: #fff; font-weight: bold; font-family: monospace; }
    .sig-roi { font-size: 12px; margin-left: 5px; opacity: 0.8; }
    .sig-long { color: #0ECB81; }
    .sig-short { color: #F6465D; }
    .sig-lev { background-color: #333; color: #FCD535; padding: 2px 5px; border-radius: 3px; }
    
    /* STRATEGY TAGS */
    .strategy-tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #333; color: #aaa; margin-right: 5px; border: 1px solid #444; display: inline-block; margin-bottom: 2px; }
    
    /* HOT COINS */
    .hot-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; font-size: 13px; }
    .hot-up { color: #0ECB81; }
    .hot-down { color: #F6465D; }
    .title-text { font-size: 35px; font-weight: bold; color: #ffffff; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. EXCHANGE CONNECTION (MEXC) ---
try:
    exchange = ccxt.mexc({
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
except:
    exchange = ccxt.binanceus({'options': {'defaultType': 'spot'}})

# --- 4. DATA FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_symbols():
    try:
        mkts = exchange.load_markets(reload=True)
        symbols = [s for s in mkts if "/USDT" in s]
        return symbols
    except: return ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "AI/USDT:USDT"]

@st.cache_data(ttl=60)
def get_hot_coins():
    try:
        tickers = exchange.fetch_tickers()
        usdt_tickers = {k: v for k, v in tickers.items() if '/USDT' in k}
        sorted_t = sorted(usdt_tickers.items(), key=lambda x: float(
