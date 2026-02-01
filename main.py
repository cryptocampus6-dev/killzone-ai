import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np
import time
import os

# --- 1. PAGE CONFIGURATION ---
page_icon = "logo.png" if os.path.exists("logo.png") else "💎"
st.set_page_config(page_title="KillZone AI - GOD MODE", layout="wide", page_icon=page_icon)

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #eaecef; font-family: 'Roboto', sans-serif; }
    [data-testid="stSidebar"] { background-color: #1e2329; border-right: 1px solid #2b3139; }
    
    /* PRO CARD DESIGN */
    .signal-box {
        background: linear-gradient(135deg, #1e2329 0%, #2b3139 100%);
        border: 1px solid #444;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    }
    .sig-header { color: #FCD535; font-size: 22px; font-weight: 800; margin-bottom: 20px; border-bottom: 1px solid #555; padding-bottom: 10px; letter-spacing: 1px; }
    .sig-row { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 16px; align-items: center; }
    .sig-label { color: #848e9c; font-weight: 500; }
    .sig-val { color: #fff; font-weight: bold; font-family: monospace; font-size: 17px; }
    
    /* COLOR CLASSES */
    .sig-long { color: #0ECB81 !important; text-shadow: 0 0 10px rgba(14, 203, 129, 0.3); }
    .sig-short { color: #F6465D !important; text-shadow: 0 0 10px rgba(246, 70, 93, 0.3); }
    .sig-neutral { color: #FCD535 !important; }
    
    /* BADGES */
    .badge { padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 5px; }
    .badge-smc { background-color: #6C5CE7; color: white; }
    .badge-vol { background-color: #00CEC9; color: black; }
    .badge-fib { background-color: #FD79A8; color: white; }

    /* HOT COINS */
    .hot-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #333; font-size: 14px; }
    .title-text { font-size: 40px; font-weight: 900; background: -webkit-linear-gradient(#eee, #999); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. EXCHANGE CONNECTION (MEXC) ---
try:
    exchange = ccxt.mexc({
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
except:
    exchange = ccxt.binanceus({'options': {'defaultType': 'spot'}}) # Backup

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
        sorted_t = sorted(usdt_tickers.items(), key=lambda x: float(x[1].get('percentage', 0) or 0), reverse=True)
        return sorted_t[:10]
    except: return []

def get_data(symbol, tf, limit=200):
    try:
        bars = exchange.fetch_ohlcv(symbol, tf, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except: return pd.DataFrame()

# --- 5. ADVANCED ANALYSIS ENGINE (GOD MODE) ---
def analyze_god_mode(df):
    # 1. Standard Indicators
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['sma200'] = ta.sma(df['close'], 200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    
    # 2. Volume Analysis (News Proxy)
    df['vol_sma'] = ta.sma(df['volume'], 20)
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 3. SMC / ICT (Fair Value Gaps - FVG)
    # Bullish FVG: Low of candle 3 > High of candle 1 (in a 3 candle sequence)
    # We check the last closed candle for FVG
    fvg_bullish = df.iloc[-3]['high'] < df.iloc[-1]['low'] and df.iloc[-2]['close'] > df.iloc[-2]['open']
    fvg_bearish = df.iloc[-3]['low'] > df.iloc[-1]['high'] and df.iloc[-2]['close'] < df.iloc[-2]['open']
    
    # 4. Fibonacci Retracement (Golden Zone Check)
    # Find High/Low of last 50 candles
    recent_high = df['high'].rolling(50).max().iloc[-1]
    recent_low = df['low'].rolling(50).min().iloc[-1]
    fib_range = recent_high - recent_low
    fib_618 = recent_high - (fib_range * 0.618) # Bullish Golden Zone
    fib_50 = recent_high - (fib_range * 0.5)
    
    # Distance to Fib Levels
    in_golden_zone_long = abs(curr['close'] - fib_618) < (curr['atr'] * 2)
    in_golden_zone_short = abs(curr['close'] - fib_50) < (curr['atr'] * 2)

    # --- SCORING SYSTEM (WEIGHTED) ---
    score = 50 # Start neutral
    reasons = []
    
    # A. Trend (SMA) - 15 Points
    if curr['close'] > curr['sma50']: 
        score += 15
        trend = "BULLISH"
    else: 
        score -= 15
        trend = "BEARISH"
        
    # B. Momentum (RSI) - 20 Points
    if curr['rsi'] < 35: 
        score += 20
        reasons.append("Oversold (RSI)")
    elif curr['rsi'] > 65: 
        score -= 20
        reasons.append("Overbought (RSI)")
        
    # C. SMC/ICT (FVG) - 15 Points
    if fvg_bullish:
        score += 15
        reasons.append("Bullish FVG (SMC)")
    if fvg_bearish:
        score -= 15
        reasons.append("Bearish FVG (SMC)")
        
    # D. Fibonacci - 10 Points
    if in_golden_zone_long and trend == "BULLISH":
        score += 10
        reasons.append("Fib 0.618 Zone")
    if in_golden_zone_short and trend == "BEARISH":
        score -= 10
        reasons.append("Fib 0.5 Zone")

    # E. Volume Spike (News/Whale Activity) - 10 Points
    if curr['volume'] > (curr['vol_sma'] * 1.5):
        if curr['close'] > curr['open']:
            score += 10
            reasons.append("High Vol Pump (News?)")
        else:
            score -= 10
            reasons.append("High Vol Dump (News?)")

    # Final Decision
    sig = "NEUTRAL"
    if score >= 70: sig = "LONG"
    elif score <= 30: sig = "SHORT"
    
    return sig, score, curr['close'], curr['atr'], reasons, trend

def calc_smart_trade(sig, price, atr):
    if sig == "NEUTRAL": return 1, 0, [0]*4, [0]*4, 0
    
    # SMC Style tight SL
    sl_dist = atr * 1.2 # Tighter SL for higher R:R
    
    if sig == "LONG":
        sl = price - sl_dist
        risk = price - sl
        tps = [price + risk*2, price + risk*3, price + risk*5, price + risk*8] # High R:R
    else:
        sl = price + sl_dist
        risk = sl - price
        tps = [price - risk*2, price - risk*3, price - risk*5, price - risk*8]
        
    risk_pct = (risk / price)
    # Leverage safety logic
    lev = min(int(0.50 / risk_pct), 50) if risk_pct > 0 else 5
    lev = max(1, lev)
    
    def get_roi(entry, target, lev):
        return abs((target - entry) / entry) * lev * 100
        
    tp_rois = [get_roi(price, tp, lev) for tp in tps]
    sl_roi = get_roi(price, sl, lev)
    
    return lev, sl, tps, tp_rois, sl_roi

# --- 6. UI RENDER ---
with st.sidebar:
    st.markdown("### 🧬 SYSTEM PARAMETERS")
    
    all_syms = get_symbols()
    if "AI/USDT:USDT" not in all_syms: all_syms.append("AI/USDT:USDT")
    
    search_mode = st.radio("Mode:", ["Select", "Type"], horizontal=True, label_visibility="collapsed")
    if search_mode == "Select":
        symbol = st.selectbox("ASSET", all_syms, index=0)
    else:
        user_input = st.text_input("SYMBOL", "BTC")
        symbol = f"{user_input.upper()}/USDT:USDT"
    
    tf = st.selectbox("TIMEFRAME", ["5m", "15m", "1h", "4h"], index=1)
    
    st.markdown("---")
    st.markdown("### 📊 MARKET SCANNER")
    hot_list = get_hot_coins()
    if hot_list:
        for s, d in hot_list:
            pct = d.get('percentage', 0) or 0
            color = "#0ECB81" if pct > 0 else "#F6465D"
            st.markdown(f"<div class='hot-item'><span>{s.split(':')[0]}</span><span style='color:{color}'>{pct:.2f}%</span></div>", unsafe_allow_html=True)

c1, c2 = st.columns([1, 6])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png", width=80)
    else: st.markdown("<h1>🧬</h1>", unsafe_allow_html=True)
with c2:
    display_sym = symbol.split(':')[0]
    st.markdown(f"<div class='title-text'>KILLZONE AI <span style='font-size:20px; color:#555'>| {display_sym}</span></div>", unsafe_allow_html=True)

if st.button("RUN GOD MODE ANALYSIS ⚡", use_container_width=True):
    with st.spinner(f'Analyzing {display_sym} with SMC, ICT, & Fibonacci Logic...'):
        df = get_data(symbol, tf)
    
    if not df.empty:
        sig, score, price, atr, reasons, trend = analyze_god_mode(df)
        lev, sl, tps, tp_rois, sl_roi = calc_smart_trade(sig, price, atr)
        
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            # Signal Card
            color_cls = "sig-long" if sig == "LONG" else ("sig-short" if sig == "SHORT" else "sig-neutral")
            
            st.markdown(f"""
            <div class="signal-box">
                <div class="sig-header">AI GENERATED SIGNAL</div>
                <div class="sig-row"><span class="sig-label">DECISION</span><span class="sig-val {color_cls}" style="font-size:24px">{sig}</span></div>
                <div class="sig-row"><span class="sig-label">SCORE</span><span class="sig-val">{score}/100</span></div>
                <div class="sig-row"><span class="sig-label">TREND</span><span class="sig-val">{trend}</span></div>
            """, unsafe_allow_html=True)
            
            if sig != "NEUTRAL":
                st.markdown(f"""
                <div class="sig-row"><span class="sig-label">LEVERAGE</span><span class="sig-val sig-neutral">Isolated {lev}x</span></div>
                <div class="sig-row"><span class="sig-label">ENTRY</span><span class="sig-val">${price:.5f}</span></div>
                <hr style="border-color:#444; margin: 15px 0">
                <div class="sig-row"><span class="sig-label">TP 1 (Conservative)</span><span class="sig-val sig-long">${tps[0]:.5f} <span class="badge badge-vol">+{tp_rois[0]:.0f}%</span></span></div>
                <div class="sig-row"><span class="sig-label">TP 2 (Standard)</span><span class="sig-val sig-long">${tps[1]:.5f} <span class="badge badge-vol">+{tp_rois[1]:.0f}%</span></span></div>
                <div class="sig-row"><span class="sig-label">TP 3 (SMC Target)</span><span class="sig-val sig-long">${tps[2]:.5f} <span class="badge badge-vol">+{tp_rois[2]:.0f}%</span></span></div>
                <div class="sig-row"><span class="sig-label">STOP LOSS</span><span class="sig-val sig-short">${sl:.5f} <span class="badge">-{sl_roi:.0f}%</span></span></div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Logic Explanation
            st.markdown("### 🧠 AI LOGIC")
            for r in reasons:
                if "FVG" in r: st.markdown(f"- <span class='badge badge-smc'>{r}</span>", unsafe_allow_html=True)
                elif "Fib" in r: st.markdown(f"- <span class='badge badge-fib'>{r}</span>", unsafe_allow_html=True)
                elif "Vol" in r: st.markdown(f"- <span class='badge badge-vol'>{r}</span>", unsafe_allow_html=True)
                else: st.markdown(f"- {r}")

        with col_right:
            # Advanced Chart
            fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=650, title=f"{display_sym} INSTITUTIONAL CHART", xaxis_rangeslider_visible=False)
            
            # Add EMA 50
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma50'], line=dict(color='yellow', width=1), name='Trend (SMA 50)'))
            
            if sig != "NEUTRAL":
                fig.add_hline(y=price, line_color="white", line_dash="dash", annotation_text="ENTRY")
                fig.add_hline(y=tps[0], line_color="#0ECB81", line_dash="dot", annotation_text="TP 1")
                fig.add_hline(y=tps[2], line_color="#0ECB81", annotation_text="TP 3 (SMC)")
                fig.add_hline(y=sl, line_color="#F6465D", annotation_text="SL")
                
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(f"MEXC Data Error for {symbol}. Try another coin.")
