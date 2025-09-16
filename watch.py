import os
import re
import json
import time
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask

# ======= NASTAVITVE =======
INTERVAL_SECONDS = 60  # koliko pogosto preverja
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEEN_FILE = "seen.json"

SITES = [
    ("https://www.bolha.com/podarim", "Bolha - Podarim"),
    ("https://www.podarimo.si/podarim/vsi-oglasi/stran-1", "Podarimo.si - Podarim"),
]

# ======= FLASK FAKE SERVER =======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# ======= POMOŽNE FUNKCIJE =======
def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen(seen):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(seen)), f, ensure_ascii=False, indent=2)
    except:
        pass

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Manjka BOT_TOKEN ali CHAT_ID")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
        requests.post(url, data=data, timeout=15)
    except Exception as e:
        print("Telegram error:", e)

def fetch(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.text

def absolutize(base_url, href):
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base_url)
        if m:
            return m.group(1) + href
    return href

def extract_items(url, html):
    soup = BeautifulSoup(html, "html.parser")
    found = []

    for a in soup.find_all("a", href=True):
        href = absolutize(url, a["href"])

        # BOLHA: samo /podarim oglasi
        if "bolha.com" in href:
            if "/podarim" not in href:
                continue
            if not re.search(r"/oglas/|/oglasi/", href):
                continue
            title = a.get_text(" ", strip=True) or "Oglas"
            found.append((href.split("?")[0], title))
            continue

        # PODARIMO.SI: vsi oglasi
        if "podarimo.si" in href:
            if "/oglas/" in href or "/podarim/" in href:
                title = a.get_text(" ", strip=True) or "Oglas"
                found.append((href.split("?")[0], title))
            continue

    uniq = []
    seen = set()
    for link, title in found:
        if link not in seen:
            seen.add(link)
            uniq.append((link, title))
    return uniq

# ======= GLAVNI LOOP =======
def run_bot():
    seen = load_seen()
    first_run = len(seen) == 0
    print(f"Bot zagnan. Že videnih: {len(seen)}")

    while True:
        try:
            for url, label in SITES:
                try:
                    html = fetch(url)
                    items = extract_items(url, html)
                    new_items = [(l, t) for (l, t) in items if l not in seen]

                    if new_items and not first_run:
                        for l, t in new_items:
                            send_telegram(f"🆕 {label}\n{t}\n{l}")

                    for l, _ in new_items:
                        seen.add(l)
                except Exception as e:
                    print("Napaka pri obdelavi:", label, e)

            save_seen(seen)
            first_run = False

        except Exception as e:
            print("Napaka v glavni zanki:", e)

        time.sleep(INTERVAL_SECONDS)

# ======= ZAŽENI BOT V OZADJU =======
if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=10000)
