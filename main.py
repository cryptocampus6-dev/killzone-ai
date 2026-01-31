import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import time
import os

# --- 1. PAGE CONFIGURATION ---
page_icon = "logo.png" if os.path.exists("logo.png") else "☣️"
st.set_page_config(page_title="KillZone Pro Futures", layout="wide", page_icon=page_icon)

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #eaecef; font-family: sans-serif; }
    [data-testid="stSidebar"] { background-color: #1e2329; border-right: 1px solid #2b3139; }
    
    /* SIGNAL CARD CSS */
    .signal-box {
        background-color: #1e2329;
        border: 1px solid #2b3139;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .sig-header { color: #FCD535; font-size: 20px; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #444; padding-bottom: 10px; }
    .sig-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 15px; }
    .sig-label { color: #848e9c; }
    .sig-val { color: #fff; font-weight: bold; font-family: monospace; }
    .sig-roi { font-size: 12px; margin-left: 5px; opacity: 0.8; }
    .sig-long { color: #0ECB81; }
    .sig-short { color: #F6465D; }
    .sig-lev { background-color: #333; color: #FCD535; padding: 2px 5px; border-radius: 3px; }
    
    /* HOT COINS */
    .hot-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; font-size: 13px; }
    .hot-up { color: #0ECB81; }
    .hot-down { color: #F6465D; }
    
    /* LOGO TITLE FIX (White Color) */
    .title-text { 
        font-size: 35px; 
        font-weight: bold; 
        color: #ffffff;
        margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. BINANCE CONNECTION ---
exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})

# --- 4. DATA FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_symbols():
    try:
        mkts = exchange.load_markets(reload=True)
        symbols = [s for s in mkts if "/USDT" in s and ":USDT" not in s] 
        symbols.sort()
        return symbols
    except: return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AI/USDT", "PEPE/USDT"]

@st.cache_data(ttl=60)
def get_hot_coins():
    try:
        tickers = exchange.fetch_tickers()
        sorted_t = sorted(tickers.items(), key=lambda x: float(x[1]['percentage'] or 0), reverse=True)
        return sorted_t[:10]
    except: return []

def get_data(symbol, tf, limit=150):
    try:
        if "/USDT" not in symbol: symbol += "/USDT"
        bars = exchange.fetch_ohlcv(symbol, tf, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except: return pd.DataFrame()

# --- 5. SIGNAL LOGIC & ROI MATH ---
def analyze(df):
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    curr = df.iloc[-1]
    
    trend = "BULLISH" if curr['close'] > curr['sma50'] else "BEARISH"
    score = 50 + (10 if trend == "BULLISH" else -10)
    if curr['rsi'] < 30: score += 20
    elif curr['rsi'] > 70: score -= 20
    
    sig = "LONG" if score >= 60 else ("SHORT" if score <= 40 else "NEUTRAL")
    return sig, score, curr['close'], curr['atr']

def calc_roi(entry, target, leverage, direction):
    if direction == "LONG":
        pct = ((target - entry) / entry) * leverage * 100
    else: # SHORT
        pct = ((entry - target) / entry) * leverage * 100
    return pct

def calc_trade(sig, price, atr):
    if sig == "NEUTRAL": return 1, 0, [0]*4, [0]*4, 0
    
    if sig == "LONG":
        sl = price - (atr * 1.5)
        risk = price - sl
        tps = [price + risk*1.5, price + risk*2.5, price + risk*3.5, price + risk*4.5]
        risk_pct = (risk / price)
        lev = min(int(0.60 / risk_pct), 75) if risk_pct > 0 else 5
        
    else:
        sl = price + (atr * 1.5)
        risk = sl - price
        tps = [price - risk*1.5, price - risk*2.5, price - risk*3.5, price - risk*4.5]
        risk_pct = (risk / price)
        lev = min(int(0.60 / risk_pct), 75) if risk_pct > 0 else 5
        
    lev = max(1, lev)
    tp_rois = [calc_roi(price, tp, lev, sig) for tp in tps]
    sl_roi = calc_roi(price, sl, lev, sig)
    
    return lev, sl, tps, tp_rois, sl_roi

# --- 6. UI RENDER ---
with st.sidebar:
    st.markdown("### ⚙️ SETTINGS")
    search_mode = st.radio("Search Mode:", ["List Select", "Type Manually"], horizontal=True)
    if search_mode == "List Select":
        all_syms = get_symbols()
        if "AI/USDT" not in all_syms: all_syms.append("AI/USDT")
        symbol = st.selectbox("COIN", all_syms, index=0)
    else:
        user_input = st.text_input("TYPE COIN (e.g. ZEC, AI)", "ZEC")
        symbol = user_input.upper()
        if "/USDT" not in symbol: symbol += "/USDT"
    
    tf = st.selectbox("TIMEFRAME", ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"], index=3)
    
    st.markdown("### 🔥 HOT COINS")
    for s, d in get_hot_coins():
        cls = "hot-up" if d['percentage'] > 0 else "hot-down"
        st.markdown(f"<div class='hot-item'><span>{s.split(':')[0]}</span><span class='{cls}'>{d['percentage']:.2f}%</span></div>", unsafe_allow_html=True)

# --- LOGO & HEADER SECTION ---
c_logo, c_title = st.columns([1, 8])

with c_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)
    elif os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=100)
    else:
        st.markdown("# ☣️")

with c_title:
    st.markdown(f"<div class='title-text'>KILLZONE PRO: {symbol} [{tf}]</div>", unsafe_allow_html=True)

# --- MAIN ANALYSIS BUTTON ---
if st.button("START ANALYSIS 🚀"):
    df = get_data(symbol, tf)
    
    if not df.empty:
        sig, score, price, atr = analyze(df)
        lev, sl, tps, tp_rois, sl_roi = calc_trade(sig, price, atr)
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            color_cls = "sig-long" if sig == "LONG" else "sig-short"
            
            if sig != "NEUTRAL":
                st.markdown(f"""
                <div class="signal-box">
                    <div class="sig-header">OFFICIAL SIGNAL 📡</div>
                    <div class="sig-row"><span class="sig-label">DIRECTION</span><span class="sig-val {color_cls}" style="font-size:20px">{sig}</span></div>
                    <div class="sig-row"><span class="sig-label">CONFIDENCE</span><span class="sig-val">{score}%</span></div>
                    <div class="sig-row"><span class="sig-label">LEVERAGE</span><span class="sig-val sig-lev">Isolated {lev}x</span></div>
                    <div class="sig-row"><span class="sig-label">ENTRY</span><span class="sig-val">${price:.5f}</span></div>
                    <hr style="border-color:#444">
                    <div class="sig-row"><span class="sig-label">TP 1</span><span class="sig-val sig-long">${tps[0]:.5f} <span class="sig-roi">(+{tp_rois[0]:.0f}%)</span></span></div>
                    <div class="sig-row"><span class="sig-label">TP 2</span><span class="sig-val sig-long">${tps[1]:.5f} <span class="sig-roi">(+{tp_rois[1]:.0f}%)</span></span></div>
                    <div class="sig-row"><span class="sig-label">TP 3</span><span class="sig-val sig-long">${tps[2]:.5f} <span class="sig-roi">(+{tp_rois[2]:.0f}%)</span></span></div>
                    <div class="sig-row"><span class="sig-label">TP 4</span><span class="sig-val sig-long">${tps[3]:.5f} <span class="sig-roi">(+{tp_rois[3]:.0f}%)</span></span></div>
                    <hr style="border-color:#444">
                    <div class="sig-row"><span class="sig-label">STOP LOSS</span><span class="sig-val sig-short">${sl:.5f} <span class="sig-roi">({sl_roi:.0f}%)</span></span></div>
                    <div class="sig-row"><span class="sig-label">R:R RATIO</span><span class="sig-val">1 : 4.5</span></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("Market is Neutral. No Trade Setup.")

        with c2:
            fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            
            fig.update_layout(
                template="plotly_dark", 
                height=600, 
                title=f"{symbol} - {tf} CHART",
                xaxis_rangeslider_visible=True, 
                hovermode='x unified', 
                xaxis=dict(showspikes=True, spikemode='across', spikecolor='yellow'), 
                yaxis=dict(showspikes=True, spikemode='across', spikecolor='yellow', side='right')
            )
            
            if sig != "NEUTRAL":
                fig.add_hline(y=price, line_color="white", annotation_text="ENTRY")
                fig.add_hline(y=tps[0], line_color="#0ECB81", line_dash="dot", annotation_text=f"TP 1 (+{tp_rois[0]:.0f}%)")
                fig.add_hline(y=tps[3], line_color="#0ECB81", line_dash="solid", annotation_text=f"TP 4 (+{tp_rois[3]:.0f}%)")
                fig.add_hline(y=sl, line_color="#F6465D", line_dash="solid", annotation_text=f"SL ({sl_roi:.0f}%)")
                
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.error(f"Could not load data for {symbol}. Check internet or coin name.")
else:
    st.info("Select Coin -> Click START ANALYSIS")