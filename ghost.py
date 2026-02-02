import streamlit as st
import requests

# --- SETTINGS ---
# ඔයාගේ කෝඩ් එකේ තිබුණ Token සහ ID එක
TELEGRAM_BOT_TOKEN = "8524773131:AAFuDVevQzNUwYeehLjQ3M-qK8QsmoaYK8c"
CHANNEL_ID = "-1003731551541"

st.set_page_config(page_title="Ghost Protocol Debugger", page_icon="🐞", layout="centered")

def send_debug_message():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHANNEL_ID, "text": "🔔 This is a TEST message from Ghost Protocol!"}
    
    try:
        r = requests.post(url, data=params)
        return r.json() # සම්පූර්ණ විස්තරයම එවනවා
    except Exception as e:
        return {"ok": False, "error": str(e)}

def main():
    st.title("🐞 Debugger Mode")
    st.write("අපි බලමු ඇයි මැසේජ් එක යන්නේ නැත්තේ කියලා.")

    if st.button("🔴 Click Here to Test Telegram"):
        with st.spinner("Sending message..."):
            result = send_debug_message()
            
            st.write("---")
            st.subheader("📡 Telegram Response:")
            st.json(result)  # මෙන්න මෙතන එරර් එක පෙන්නයි
            
            if result.get("ok"):
                st.success("✅ වැඩේ ගොඩ! මැසේජ් එක ගියා.")
            else:
                st.error("❌ අවුලක් තියෙනවා! පහත Error එක බලන්න:")
                # වැරැද්ද පැහැදිලිව පෙන්වන්න
                st.code(result.get("description"), language="text")

if __name__ == "__main__":
    main()
