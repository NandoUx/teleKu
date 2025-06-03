import os
from instagrapi import Client
from dotenv import load_dotenv
from flask import Flask, request
import requests

load_dotenv()

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Login Instagram saat startup
cl = Client()
print("Login IG...")
cl.login(IG_USERNAME, IG_PASSWORD)
print("Instagram login successful!")

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return {"ok": True}

    if text.lower() == "test ig":
        send_message(chat_id, "✅ Instagram login berhasil! Siap upload / scrape.")
    else:
        send_message(chat_id, "Kirim 'test ig' untuk cek koneksi Instagram.")

    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
