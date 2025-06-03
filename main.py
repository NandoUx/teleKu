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

cl = Client()
cl.login(IG_USERNAME, IG_PASSWORD)

def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if "test ig" in text.lower():
        send_message(chat_id, "🔐 Login ke Instagram sukses, akun siap digunakan!")
    else:
        send_message(chat_id, "Kirim 'test ig' untuk uji login ke Instagram.")

    return {"ok": True}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
