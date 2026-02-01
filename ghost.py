import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests
import pytz
from datetime import datetime, timedelta

# --- 1. USER SETTINGS ---
TELEGRAM_BOT_TOKEN = "8524773131:AAFuDVevQzNUwYeehLjQ3M-qK8QsmoaYK8c"
CHANNEL_ID = "-1003731551541"
STICKER_ID = "CAACAgUAAxkBAAEQZgNpf0jTNnM9QwNCwqMbVuf-AAE0x5oAAvsKAAIWG_BWIMq--iOTVBE4BA"

# --- 2. COMPLETE BINANCE FUTURES COIN LIST ---
DEFAULT_COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "SHIB", "AVAX", "DOT", "MATIC", "LTC", "TRX", "LINK", "UNI", "ATOM", "NEAR", "ALGO", "BCH", "FIL", "XLM", "VET", "ICP", "SAND", "MANA", "AXS", "THETA", "AAVE", "EOS", "XTZ", "KLAY", "RUNE", "EGLD", "FTM", "CRV", "FLOW", "KAVA", "GALA", "HBAR", "MINA", "CHZ", "DYDX", "AR", "QNT", "STX", "CVX", "ENJ", "BAT", "COMP", "HOT", "1INCH", "IOTA", "GRT", "RVN", "ZIL", "ETC", "DASH", "WAVES", "OMG", "ICX", "QTUM", "ZRX", "IOST", "ONT", "ZEC", "NEO", "SXP", "SNX", "MKR", "YFI", "SUSHI", "UMA", "YFII", "KSM", "REN", "OCEAN", "RSR", "LRC", "BAL", "KNC", "BNT", "BAND", "OGN", "CTSI", "STORJ", "SKL", "ALICE", "ALPHA", "ANKR", "ARPA", "ATA", "AUDIO", "BAKE", "BEL", "BLZ", "C98", "CELO", "CELR", "CHR", "CKB", "COTI", "CTK", "DENT", "DGB", "DODO", "FLM", "GTC", "HIVE", "HNT", "IDEX", "IOTX", "LINA", "LIT", "LPT", "MASK", "MTL", "NKN", "ONE", "ONG", "PEOPLE", "PERP", "RARE", "RAY", "REEF", "RLC", "ROSE", "SFP", "SLP", "SOL", "STMX", "SUN", "TFUEL", "TLM", "UNFI", "WAXP", "WIN", "XEM", "XMR", "XVS", "YGG", "ZEN", "PEPE", "FLOKI", "WIF", "BONK", "SUI", "SEI", "TIA", "ORDI", "PYTH", "JUP", "1000SHIB", "1000LUNC", "LUNA", "USTC", "OP", "ARB", "APT", "IMX", "LDO", "HOOK", "HFT", "MAGIC", "GNS", "LQTY", "ID", "JOE", "RDNT", "EDU", "SUI", "MAV", "PENDLE", "ARKM", "WLD", "CYBER", "STRK", "AXL", "PORTAL", "AEVO", "METIS", "ETHFI", "ENA", "W", "SAGA", "TAO", "OMNI", "REZ", "BB", "NOT", "IO", "ZK", "ZRO", "LISTA", "RENDER", "BANANA", "RARE", "SYS", "POPCAT", "SUN", "ALPACA", "VIDT", "MBOX", "FLOKI", "CATI", "HMSTR", "EIGEN", "NEIRO", "TURBO", "BABYDOGE", "MOODENG", "GOAT", "GRASS", "DRIFT", "SWELL", "COW", "CETUS", "PNUT", "ACT", "THE"
]

# --- 3. SETUP ---
st.set_page_config(page_title="Ghost Protocol VIP", page_icon="👻", layout="wide")
lz = pytz.timezone('Asia/Colombo')

# --- 4. FUNCTIONS ---
def send_telegram(msg, sticker=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
    try:
        if sticker:
            requests.post(url + "sendSticker", data={"chat_id": CHANNEL_ID, "sticker": STICKER_ID})
        else:
            requests.post(url + "sendMessage", data={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
    except: pass

def get_data(symbol):
    try:
        exchange = ccxt.mexc({'options': {'defaultType': 'swap'}})
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
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
    
    sig = "NEUTRAL"
    if score >= 75: sig = "LONG"
    elif score <= 25: sig = "SHORT"
    return sig, score, curr['close'], curr['atr']

# --- 5. MAIN ENGINE ---
def main():
    st.title("👻 GHOST PROTOCOL : VIP ENGINE")
    
    # Session State Initialization
    if 'coin_list' not in st.session_state:
        st.session_state.coin_list = ", ".join(DEFAULT_COINS)
    if 'signals_log' not in st.session_state:
        st.session_state.signals_log = []
    
    # 🚨 AUTO-START LOGIC: මෙතන තමයි වැඩේ වෙන්නේ
    if 'engine_running' not in st.session_state:
        st.session_state.engine_running = True # දැන් ඇප් එක ඕපන් වෙද්දීම මේක True වෙනවා

    tab1, tab2, tab3 = st.tabs(["🎛️ Control Panel", "📝 Coin Manager", "📜 History"])

    with tab1:
        time_placeholder = st.empty()
        status_placeholder = st.empty()
        
        now_init = datetime.now(lz)
        time_placeholder.metric("Sri Lanka Time 🇱🇰", now_init.strftime("%H:%M:%S"))

        st.markdown("---")

        c1, c2 = st.columns(2)
        # බොත්තම් තියෙන්නේ ඔයාට ඕන නම් විතරක් වෙනස් කරන්න
        if c1.button("🟢 MANUAL START"):
            st.session_state.engine_running = True
            st.rerun()
            
        if c2.button("🔴 EMERGENCY STOP"):
            st.session_state.engine_running = False
            st.rerun()

        log_box = st.empty()

        if st.session_state.engine_running:
            coins = [x.strip() for x in st.session_state.coin_list.split(',')]
            last_scan_time = datetime.now(lz) - timedelta(minutes=15)

            while st.session_state.engine_running:
                now_live = datetime.now(lz)
                time_placeholder.metric("Sri Lanka Time 🇱🇰", now_live.strftime("%H:%M:%S"))
                
                # Market Hour Logic
                if not (7 <= now_live.hour < 21):
                    status_placeholder.error("💤 Market Sleep Mode (Waiting for 7 AM)")
                    log_box.info("Night Mode Active 🌙")
                    time.sleep(1)
                    continue

                status_placeholder.success("✅ ENGINE RUNNING (Auto-Active)")

                time_diff = (now_live - last_scan_time).total_seconds()
                
                if time_diff >= 900: # 15 Mins
                    log_box.markdown(f"**🔄 Scanning Market... ({len(coins)} Coins)**")
                    progress_bar = st.progress(0)
                    
                    for i, coin in enumerate(coins):
                        now_scan = datetime.now(lz)
                        time_placeholder.metric("Sri Lanka Time 🇱🇰", now_scan.strftime("%H:%M:%S"))
                        
                        try:
                            df = get_data(f"{coin}/USDT:USDT")
                            if not df.empty:
                                sig, score, price, atr = analyze(df)
                                if (sig == "LONG" and score >= 75) or (sig == "SHORT" and score <= 25):
                                    send_telegram("Alert", sticker=True)
                                    sl_dist = atr * 1.5
                                    if sig == "LONG":
                                        sl = price - sl_dist
                                        tps = [price + sl_dist*1.5, price + sl_dist*2.5, price + sl_dist*3.5]
                                    else:
                                        sl = price + sl_dist
                                        tps = [price - sl_dist*1.5, price - sl_dist*2.5, price - sl_dist*3.5]
                                    
                                    rr = round(abs(tps[2]-price)/abs(price-sl), 2)
                                    msg = f"💎 <b>VIP SIGNAL</b>\n\n🪙 <b>{coin}</b>\nSignal: {sig}\nEntry: {price:.4f}\nTargets: {tps[0]:.4f} | {tps[1]:.4f} | {tps[2]:.4f}\nSL: {sl:.4f}\nRR: 1:{rr}"
                                    send_telegram(msg)
                                    st.session_state.signals_log.insert(0, f"{now_scan.strftime('%H:%M')} | {coin} | {sig}")
                        except: pass
                        progress_bar.progress((i + 1) / len(coins))
                        
                    last_scan_time = now_live
                    log_box.success(f"✅ Scan Complete at {now_live.strftime('%H:%M')}.")
                    progress_bar.empty()
                else:
                    mins_left = int((900 - time_diff) / 60)
                    log_box.info(f"⏳ Next Scan in {mins_left} minutes...")
                    time.sleep(1)

    with tab2:
        st.subheader("Manage Coins")
        txt = st.text_area("List", st.session_state.coin_list, height=300)
        if st.button("Save"): 
            st.session_state.coin_list = txt
            st.success("List Updated!")

    with tab3:
        st.subheader("History")
        for item in st.session_state.signals_log: st.text(item)

if __name__ == "__main__":
    main()
