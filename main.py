import os
import time
import random
import threading
import requests
from flask import Flask, request
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from datetime import datetime

load_dotenv()
app = Flask(__name__)

# 🔑 Env
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
SESSION_PATH = "ig_session.json"
UPLOAD_LOG_FILE = "upload_log.txt"

# 📌 Limits
DAILY_LIMIT = 10
FAIL_LIMIT = 3
last_upload_time = 0
upload_count_today = 0
upload_fail_count = 0

# 🔐 Login IG
cl = Client()
def login_instagram():
    global cl
    try:
        if os.path.exists(SESSION_PATH):
            cl.load_settings(SESSION_PATH)
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_PATH)
        print("✅ Instagram login success")
    except LoginRequired:
        print("⚠️ Login retry...")
        cl = Client()
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_PATH)
        print("✅ IG login retry success")

# 📊 Upload log
def load_upload_count():
    global upload_count_today
    today = datetime.now().date()
    if os.path.exists(UPLOAD_LOG_FILE):
        with open(UPLOAD_LOG_FILE, "r") as f:
            lines = f.readlines()
            count = sum(1 for line in lines if datetime.fromisoformat(line.strip()).date() == today)
            upload_count_today = count

def log_upload():
    with open(UPLOAD_LOG_FILE, "a") as f:
        f.write(datetime.now().isoformat() + "\n")

# 📩 Send Telegram
def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# 📥 TikTok downloader
def download_tiktok(url):
    api = f"https://tikwm.com/api/?url={url}"
    try:
        res = requests.get(api).json()
        if res.get("code") == 429:
            return None, "Rate limit"
        if res.get("data"):
            return res['data']['play'], res['data']['title']
    except Exception as e:
        print("Download error:", e)
    return None, "Gagal ambil video"

# 📤 Upload ke IG
def upload_to_instagram(video_url, caption, chat_id):
    global last_upload_time, upload_count_today, upload_fail_count
    try:
        load_upload_count()
        if upload_count_today >= DAILY_LIMIT:
            send_message(chat_id, f"🚫 Batas harian {DAILY_LIMIT} upload tercapai.")
            return

        if upload_fail_count >= FAIL_LIMIT:
            send_message(chat_id, "⚠️ Upload gagal berkali-kali. Pause otomatis.")
            return

        delay = random.randint(180, 420)  # 3–7 menit
        now = time.time()
        if now - last_upload_time < delay:
            wait = delay - (now - last_upload_time)
            send_message(chat_id, f"⏳ Tunggu {int(wait)} detik untuk upload aman...")
            time.sleep(wait)

        video_path = "video.mp4"
        r = requests.get(video_url)
        with open(video_path, "wb") as f:
            f.write(r.content)

        hashtags = ["#fyp", "#viral", "#reels", "#tiktok", "#funny", "#trending"]
        random.shuffle(hashtags)
        caption += "\n\n🔥 " + " ".join(hashtags[:3])

        send_message(chat_id, "🚀 Mengupload ke Instagram...")
        cl.clip_upload(video_path, caption)
        os.remove(video_path)

        last_upload_time = time.time()
        upload_count_today += 1
        upload_fail_count = 0
        log_upload()
        send_message(chat_id, "✅ Reels berhasil diupload!")
    except Exception as e:
        upload_fail_count += 1
        send_message(chat_id, f"❌ Gagal upload ke IG: {e}")
        print("Upload error:", e)

# 🌐 Webhook handler
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return {"ok": True, "message": "Bot is running"}

    data = request.get_json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return {"ok": True}

    if "test ig" in text.lower():
        send_message(chat_id, "🔐 Login ke Instagram sukses, akun siap digunakan!")
    elif "tiktok.com" in text:
        send_message(chat_id, "📥 Sedang download video TikTok...")
        video_url, caption = download_tiktok(text)
        if video_url:
            threading.Thread(target=upload_to_instagram, args=(video_url, caption, chat_id)).start()
        else:
            send_message(chat_id, f"❌ {caption}")
    else:
        send_message(chat_id, "Ketik 'test ig' atau kirim link TikTok.")

    return {"ok": True}

if __name__ == "__main__":
    login_instagram()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
