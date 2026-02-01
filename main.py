import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import time
import os

# --- 1. PAGE CONFIGURATION & BRANDING ---
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
        # Fixed Sorting Line
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

# --- 5. GOD MODE ANALYSIS LOGIC ---
def analyze_god_mode(df):
    df['rsi'] = ta.rsi(df['close'], 14)
    df['sma50'] = ta.sma(df['close'], 50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
    df['vol_sma'] = ta.sma(df['volume'], 20)
    
    curr = df.iloc[-1]
    
    # SMC / FVG
    fvg_bullish = df.iloc[-3]['high'] < df.iloc[-1]['low'] and df.iloc[-2]['close'] > df.iloc[-2]['open']
    fvg_bearish = df.iloc[-3]['low'] > df.iloc[-1]['high'] and df.iloc[-2]['close'] < df.iloc[-2]['open']
    
    # MSNR
    recent_high = df['high'].rolling(50).max().iloc[-1]
    recent_low = df['low'].rolling(50).min().iloc[-1]
    
    score = 50
    reasons = []
    trend = "NEUTRAL"
    
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
        
    # SMC
    if fvg_bullish:
        score += 15
        reasons.append("FVG Bull")
    if fvg_bearish:
        score -= 15
        reasons.append("FVG Bear")

    # MSNR
    if abs(curr['close'] - recent_low) < (curr['atr'] * 1.5) and trend == "BULLISH":
        score += 10
        reasons.append("Supp Bounce")
    if abs(curr['close'] - recent_high) < (curr['atr'] * 1.5) and trend == "BEARISH":
        score -= 10
        reasons.append("Resist Reject")

    # News / Volume
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
        
    risk_pct = (risk / price)
    lev = min(int(0.60 / risk_pct), 75) if risk_pct > 0 else 5
    lev = max(1, lev)
    
    def get_roi(entry, target, lev):
        return abs((target - entry) / entry) * lev * 100
        
    tp_rois = [get_roi(price, tp, lev) for tp in tps]
    sl_roi = get_roi(price, sl, lev)
    
    return lev, sl, tps, tp_rois, sl_roi

# --- 6. UI RENDER ---
with st.sidebar:
    st.markdown("### ⚙️ SETTINGS")
    
    all_syms = get_symbols()
    if "AI/USDT:USDT" not in all_syms: all_syms.append("AI/USDT:USDT")
    
    search_mode = st.radio("Search Mode:", ["List Select", "Type Manually"], horizontal=True)
    if search_mode == "List Select":
        symbol = st.selectbox("COIN", all_syms, index=0)
    else:
        user_input = st.text_input("TYPE COIN (e.g. BTC, AI)", "BTC")
        symbol = f"{user_input.upper()}/USDT:USDT" 
    
    tf = st.selectbox("TIMEFRAME", ["1m", "5m", "15m", "30m", "1h", "4h", "1d"], index=2)
    
    st.markdown("### 🔥 HOT COINS (MEXC)")
    hot_list = get_hot_coins()
    if hot_list:
        for s, d in hot_list:
            pct = d.get('percentage', 0) or 0
            cls = "hot-up" if pct > 0 else "hot-down"
            display_name = s.split(':')[0]
            st.markdown(f"<div class='hot-item'><span>{display_name}</span><span class='{cls}'>{pct:.2f}%</span></div>", unsafe_allow_html=True)

c_logo, c_title = st.columns([1, 8])
with c_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=100)
    else: st.markdown("# 🚀")

with c_title:
    display_sym = symbol.split(':')[0]
    st.markdown(f"<div class='title-text'>KILLZONE PRO: {display_sym} [{tf}]</div>", unsafe_allow_html=True)

if st.button("START ANALYSIS 🚀"):
    with st.spinner('Running GOD MODE Analysis...'):
        df = get_data(symbol, tf)
    
    if not df.empty:
        sig, score, price, atr, reasons = analyze_god_mode(df)
        lev, sl, tps, tp_rois, sl_roi = calc_trade(sig, price, atr)
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            color_cls = "sig-long" if sig == "LONG" else "sig-short"
            if sig != "NEUTRAL":
                strategy_str = "".join([f"<span class='strategy-tag'>{r}</span>" for r in reasons])
                
                st.markdown(f"""
                <div class="signal-box">
                    <div class="sig-header">OFFICIAL SIGNAL 📡</div>
                    <div class="sig-row"><span class="sig-label">DIRECTION</span><span class="sig-val {color_cls}" style="font-size:20px">{sig}</span></div>
                    <div class="sig-row"><span class="sig-label">CONFIDENCE</span><span class="sig-val">{score}%</span></div>
                    <div class="sig-row"><span class="sig-label">LEVERAGE</span><span class="sig-val sig-lev">Isolated {lev}x</span></div>
                    <div class="sig-row"><span class="sig-label">ENTRY</span><span class="sig-val">${price:.5f}</span></div>
                    <div style="margin: 10px 0;">{strategy_str}</div>
                    <hr style="border-color:#444">
                    <div class="sig-row"><span class="sig-label">TP 1</span><span class="sig-val sig-long">${tps[0]:.5f} <span class="sig-roi">(+{tp_rois[0]:.0f}%)</span></span></div>
                    <div class="sig-row"><span class="sig-label">TP 2</span><span class="sig-val sig-long">${tps[1]:.5f} <span class="sig-roi">(+{tp_rois[1]:.0f}%)</span></span></div>
                    <div class="sig-row"><span class="sig-label">TP 3</span><span class="sig-val sig-long">${tps[2]:.5f} <span class="sig-roi">(+{tp_rois[2]:.0f}%)</span></span></div>
                    <div class="sig-row"><span class="sig-label">TP 4</span><span class="sig-val sig-long">${tps[3]:.5f} <span class="sig-roi">(+{tp_rois[3]:.0f}%)</span></span></div>
                    <hr style="border-color:#444">
                    <div class="sig-row"><span class="sig-label">STOP LOSS</span><span class="sig-val sig-short">${sl:.5f} <span class="sig-roi">({sl_roi:.0f}%)</span></span></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("Market is Neutral. No Trade Setup.")

        with c2:
            fig = go.Figure(data=[go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.update_layout(template="plotly_dark", height=600, title=f"{display_sym} CHART", xaxis_rangeslider_visible=False)
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma50'], line=dict(color='yellow', width=1), name='Trend'))

            if sig != "NEUTRAL":
                fig.add_hline(y=price, line_color="white")
                fig.add_hline(y=tps[0], line_color="#0ECB81", line_dash="dot")
                fig.add_hline(y=sl, line_color="#F6465D")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Could not load data for {symbol}.")
else:
    st.info("Select Coin -> Click START ANALYSIS")
