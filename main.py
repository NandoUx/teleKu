import os
import time
import random
import requests
from flask import Flask, request
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from datetime import datetime, timedelta

load_dotenv()
app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
SESSION_PATH = "ig_session.json"

cl = Client()
last_upload_time = 0
upload_count_today = 0
upload_fail_count = 0
DAILY_LIMIT = 10
FAIL_LIMIT = 3
UPLOAD_LOG_FILE = "upload_log.txt"


# 🔒 Save & load IG session
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

# 🔄 Cek berapa kali upload hari ini
def load_upload_count():
    global upload_count_today
    today = datetime.now().date()
    if os.path.exists(UPLOAD_LOG_FILE):
        with open(UPLOAD_LOG_FILE, "r") as f:
            lines = f.readlines()
            count = 0
            for line in lines:
                ts = datetime.fromisoformat(line.strip())
                if ts.date() == today:
                    count += 1
            upload_count_today = count
    else:
        upload_count_today = 0

# 🧠 Simpan log setiap upload
def log_upload():
    with open(UPLOAD_LOG_FILE, "a") as f:
        f.write(datetime.now().isoformat() + "\n")

# Telegram reply
def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# Ambil video + caption dari TikTok
def download_tiktok(url):
    api = f"https://tikwm.com/api/?url={url}"
    res = requests.get(api).json()
    if res.get("data"):
        return res['data']['play'], res['data']['title']
    return None, None

# Upload video to IG Reels dengan delay, limiter & anti-spam
def upload_to_instagram(video_url, caption, chat_id):
    global last_upload_time, upload_count_today, upload_fail_count

    load_upload_count()
    if upload_count_today >= DAILY_LIMIT:
        send_message(chat_id, f"🚫 Sudah mencapai batas harian {DAILY_LIMIT} upload.")
        return

    if upload_fail_count >= FAIL_LIMIT:
        send_message(chat_id, f"⚠️ Upload gagal {FAIL_LIMIT}x. Bot auto pause sementara.")
        return

    now = time.time()
    delay = random.randint(180, 420)  # 3–7 menit
    if now - last_upload_time < delay:
        wait = delay - (now - last_upload_time)
        send_message(chat_id, f"⏳ Delay aman {int(wait)} detik sebelum upload...")
        time.sleep(wait)

    video_path = "video.mp4"
    r = requests.get(video_url)
    with open(video_path, "wb") as f:
        f.write(r.content)

    # Tambah sedikit randomizer ke caption
    caption += f"\n\n🔥 #tiktok {random.randint(1000,9999)}"

    try:
        send_message(chat_id, "🚀 Mengupload ke Instagram...")
        cl.clip_upload(video_path, caption)
        last_upload_time = time.time()
        upload_count_today += 1
        upload_fail_count = 0
        log_upload()
        send_message(chat_id, "✅ Reels berhasil diupload!")
    except Exception as e:
        upload_fail_count += 1
        send_message(chat_id, f"❌ Gagal upload ke IG: {e}")
        print("Upload error:", e)

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
        send_message(chat_id, "📥 Download video dari TikTok...")
        video_url, caption = download_tiktok(text)
        if video_url:
            upload_to_instagram(video_url, caption, chat_id)
        else:
            send_message(chat_id, "❌ Gagal ambil video dari TikTok.")
    else:
        send_message(chat_id, "Kirim 'test ig' atau link TikTok.")

    return {"ok": True}

if __name__ == "__main__":
    login_instagram()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
