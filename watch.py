import os
import re
import json
import time
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask

# ======= NASTAVITVE =======
INTERVAL_SECONDS = 60  # kako pogosto preverja
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEEN_FILE = "seen.json"

SITES = [
    ("https://www.bolha.com/podarim", "Bolha - Podarim"),
    ("https://www.podarimo.si/podarim/vsi-oglasi/stran-1", "Podarimo.si - Podarim"),
]

# ======= FLASK SERVER =======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running and checking for new ads!"

# ======= POMOŽNE FUNKCIJE =======
def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def fetch(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    return r.text

def extract_links(url, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/") or "bolha.com" in href or "podarimo.si" in href:
            if "oglasi" in href:
                if href.startswith("/"):
                    href = re.match(r"(https?://[^/]+)", url).group(1) + href
                links.add(href.split("?")[0])
    return links

# ======= GLAVNA FUNKCIJA =======
def main_loop():
    seen = load_seen()
    while True:
        for url, name in SITES:
            try:
                html = fetch(url)
                links = extract_links(url, html)
                new_links = [l for l in links if l not in seen]
                for l in new_links:
                    send_telegram(f"🆕 Nov oglas na {name}: {l}")
                    seen.add(l)
                save_seen(seen)
            except Exception as e:
                send_telegram(f"Napaka pri {name}: {e}")
        time.sleep(INTERVAL_SECONDS)

# ======= ZAŽENI BOT V OZADJU =======
threading.Thread(target=main_loop, daemon=True).start()

# ======= ZAŽENI FLASK SERVER =======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

