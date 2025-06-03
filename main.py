import os
import time
import requests
from flask import Flask, request
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
SESSION_PATH = "ig_session.json"

cl = Client()
last_upload_time = 0

# 🔒 Save session IG
def login_instagram():
    global cl
    try:
        if os.path.exists(SESSION_PATH):
            cl.load_settings(SESSION_PATH)
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_PATH)
        print("✅ Instagram login success")
    except LoginRequired:
        print("⚠️ Login required, retrying...")
        cl = Client()
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_PATH)
        print("✅ IG login retry success")

login_instagram()

# Telegram reply
def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# Download TikTok video using tikwm API
def download_tiktok(url):
    api = f"https://tikwm.com/api/?url={url}"
    res = requests.get(api).json()
    if res['data']:
        return res['data']['play'], res['data']['title']
    return None, None

# Upload video to IG Reels
def upload_to_instagram(video_url, caption):
    global last_upload_time
    now = time.time()
    if now - last_upload_time < 120:  # 2 minutes
        wait = 120 - (now - last_upload_time)
        print(f"⏳ Delay upload... waiting {int(wait)} seconds")
        time.sleep(wait)
    
    video_path = "video.mp4"
    r = requests.get(video_url)
    with open(video_path, "wb") as f:
        f.write(r.content)

    print("🚀 Uploading to Instagram...")
    cl.clip_upload(video_path, caption)
    last_upload_time = time.time()
    print("✅ Upload complete!")

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return {"ok": True}

    if "test ig" in text.lower():
        send_message(chat_id, "🔐 Login ke Instagram sukses, akun siap digunakan!")
    elif "tiktok.com" in text:
        send_message(chat_id, "📥 Downloading video from TikTok...")
        video_url, caption = download_tiktok(text)
        if video_url:
            send_message(chat_id, f"✅ Dapat video & caption:\n\n{caption}\n\n🚀 Uploading to IG...")
            try:
                upload_to_instagram(video_url, caption)
                send_message(chat_id, "🎉 Sukses upload ke Reels!")
            except Exception as e:
                print(f"❌ Upload failed: {e}")
                send_message(chat_id, f"❌ Gagal upload ke IG: {e}")
        else:
            send_message(chat_id, "❌ Gagal ambil video dari TikTok.")
    else:
        send_message(chat_id, "Kirim 'test ig' atau link TikTok.")

    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
