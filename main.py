

import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import time
import os

# --- 1. CONFIGURATION (BRANDING) ---
# මෙතනින් තමයි App එකේ නම සහ Icon එක තීරණය වෙන්නේ
st.set_page_config(
    page_title="KillZone Pro Trading",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLES ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #eaecef; }
    [data-testid="stSidebar"] { background-color: #1e2329; }
    .signal-box { background-color: #1e2329; border: 1px solid #2b3139; border-radius: 10px; padding: 20px; }
    .sig-val { color: #fff; font-weight: bold; font-family: monospace; }
    .sig-long { color: #0ECB81; }
    .sig-short { color: #F6465D; }
    .hot-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; font-size: 13px; }
    .hot-up { color: #0ECB81; }
    .hot-down { color: #F6465D; }
    .title-text { font-size: 35px; font-weight: bold; color: #ffffff; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. HTML GENERATOR (ERROR-PROOF) ---
def create_card_html(sig, score, lev, price, reasons, tps, sl, tp_rois, sl_roi):
    color = "sig-long" if sig == "LONG" else "sig-short"
    reasons_txt = " | ".join(reasons)
    
    html = f"""
    <div class="signal-box">
        <div style="color:#FCD535; font-size:20px; border-bottom:1px solid #444; margin-bottom:10px;">OFFICIAL SIGNAL 📡</div>
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>TYPE</span><span class="{color}" style="font-size:22px; font-weight:bold">{sig}</span></div>
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>SCORE</span><span>{score}%</span></div>
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>LEV</span><span style="background:#333; color:#FCD535; padding:2px 5px; border-radius:3px;">Isolated {lev}x</span></div>
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>ENTRY</span><span class="sig-val">${price:.5f}</span></div>
        <div style="font-size:12px; color:#aaa; margin:10px 0;">{reasons_txt}</div>
        <hr style="border-color:#444">
        <div style="display:flex; justify-content:space-between;"><span>TP 1</span><span class="sig-long">${tps[0]:.5f} <span style="font-size:11px">({tp_rois[0]:.0f}%)</span></span></div>
        <div style="display:flex; justify-content:space-between;"><span>TP 2</span><span class="sig-long">${tps[1]:.5f} <span style="font-size:11px">({tp_rois[1]:.0f}%)</span></span></div>
        <div style="display:flex; justify-content:space-between;"><span>TP 3</span><span class="sig-long">${tps[2]:.5f} <span style="font-size:11px">({tp_rois[2]:.0f}%)</span></span></div>
        <hr style="border-color:#444">
        <div style="display:flex; justify-content:space-between;"><span>STOP</span><span class="sig-short">${sl:.5f} <span style="font-size:11px">({sl_roi:.0f}%)</span></span></div>
    </div>
    """
    return html

# --- 4. EXCHANGE SETUP ---
try:
    exchange = ccxt.mexc({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})
except:
    exchange = ccxt.binanceus({'options': {'defaultType': 'spot'}})

# --- 5. DATA FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_symbols():
    try:
        mkts = exchange.load_markets(reload=True)
        return [s for s in mkts if "/USDT" in s]
    except: return ["BTC/USDT:USDT", "ETH/USDT:USDT"]

@st.cache_data(ttl=60)
def get_hot_coins():
    try:
        tickers = exchange.fetch_tickers()
        valid = []
        for s, d in tickers.items():
            if "/USDT" in s and d.get('percentage') is not None:
                valid.append((s, float(d['percentage'])))
        valid.sort(key=lambda x: x[1], reverse=True)
        return valid[:10]
    except: return []

def get_data(symbol, tf, limit=200):
    try:
        bars = exchange.fetch_ohlcv(symbol, tf, limit=limit)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except: return pd.DataFrame()

# --- 6. ANALYSIS LOGIC (GOD MODE) ---
def analyze_god_mode(df):
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    df['vol_sma'] = ta.sma(df['volume'], 20)
    
    curr = df.iloc[-1]
    score = 50
    reasons = []
    
    # Trend
    if curr['close'] > curr['sma50']: 
        score += 15
        trend = "BULLISH"
    else: 
        score -= 15
        trend = "BEARISH"
        
    # RSI
    if curr['rsi'] < 30: 
        score += 20
        reasons.append("Oversold")
    elif curr['rsi'] > 70: 
        score -= 20
        reasons.append("Overbought")

    # Volume/News
    if curr['volume'] > (curr['vol_sma'] * 1.5):
        reasons.append("High Vol (News?)")
        if curr['close'] > curr['open']: score += 10
        else: score -= 10

    sig = "NEUTRAL"
    if score >= 65: sig = "LONG"
    elif score <= 35: sig = "SHORT"
    
    return sig, score, curr['close'], curr['atr'], reasons

def calc_trade(sig, price, atr):
    if sig == "NEUTRAL": return 1, 0, [0]*4, [0]*4, 0
    
    sl_dist = atr * 1.5 
    if sig == "LONG":
        sl = price - sl_dist
        risk = price - sl
        tps = [price + risk*1.5, price + risk*2.5, price + risk*3.5, price + risk*4.5]
    else:
        sl = price + sl_dist
        risk = sl - price
        tps = [price - risk*1.5, price - risk*2.5, price - risk*3.5, price - risk*4.5]
        
    risk_pct = (risk / price) if price > 0 else 0
    lev = max(1, min(int(0.60 / risk_pct), 75)) if risk_pct > 0 else 5
    
    tp_rois = [abs((tp - price)/price)*lev*100 for tp in tps]
    sl_roi = abs((sl - price)/price)*lev*100
    
    return lev, sl, tps, tp_rois, sl_roi

# --- 7. MAIN APP UI ---
def main():
    with st.sidebar:
        st.markdown("### ⚙️ SETTINGS")
        all_syms = get_symbols()
        if "AI/USDT:USDT" not in all_syms: all_syms.append("AI/USDT:USDT")
        
        search_mode = st.radio("Search:", ["List", "Type"], horizontal=True)
        if search_mode == "List": symbol = st.selectbox("COIN", all_syms)
        else: symbol = st.text_input("COIN", "BTC").upper() + "/USDT:USDT"
        
        tf = st.selectbox("TIMEFRAME", ["5m", "15m", "1h", "4h"], index=1)
        
        st.markdown("### 🔥 HOT COINS")
        for s, p in get_hot_coins():
            cls = "hot-up" if p > 0 else "hot-down"
            st.markdown(f"<div class='hot-item'><span>{s.split(':')[0]}</span><span class='{cls}'>{p:.2f}%</span></div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 8])
    with c1: 
        if os.path.exists("logo.png"): st.image("logo.png", width=100)
        else: st.markdown("🚀")
    with c2: st.markdown(f"<div class='title-text'>KILLZONE PRO: {symbol.split(':')[0]} [{tf}]</div>", unsafe_allow_html=True)

    if st.button("START ANALYSIS 🚀"):
        with st.spinner('Analyzing...'):
            df = get_data(symbol, tf)
        
        if not df.empty:
            sig, score, price, atr, reasons = analyze_god_mode(df)
            lev, sl, tps, tp_rois, sl_roi = calc_trade(sig, price, atr)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                if sig != "NEUTRAL":
                    # Generating HTML safely
                    html_code = create_card_html(sig, score, lev, price, reasons, tps, sl, tp_rois, sl_roi)
                    st.markdown(html_code, unsafe_allow_html=True)
                else: 
                    st.warning("Neutral Market - No Trade")
                
            with col2:
                fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
                fig.update_layout(template="plotly_dark", height=600, title=f"{symbol.split(':')[0]} CHART", xaxis_rangeslider_visible=False)
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma50'], line=dict(color='yellow', width=1), name='Trend'))
                if sig != "NEUTRAL":
                    fig.add_hline(y=price, line_color="white", line_dash="dash")
                    fig.add_hline(y=tps[0], line_color="#0ECB81", line_dash="dot")
                    fig.add_hline(y=sl, line_color="#F6465D")
                st.plotly_chart(fig, use_container_width=True)
        else: st.error("Data Error. Try another coin.")

if __name__ == "__main__":
    main()
