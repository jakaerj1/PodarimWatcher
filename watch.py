import os, time, json, re, requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
INTERVAL = 60  # sekunde

SITES = [
    ("https://www.bolha.com/podarim", "Bolha - Podarim"),
    ("https://www.podarimo.si/podarim/vsi-oglasi/stran-1", "Podarimo.si - Podarim"),
]

SEEN_FILE = "seen.json"

def load_seen():
    return set(json.load(open(SEEN_FILE))) if os.path.exists(SEEN_FILE) else set()

def save_seen(seen):
    json.dump(list(seen), open(SEEN_FILE, "w"))

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
        if href.startswith("/"):
            href = re.match(r"(https?://[^/]+)", url).group(1) + href
        if "oglas" in href or "oglasi" in href:
            links.add(href.split("?")[0])
    return links

def main():
    seen = load_seen()
    first = True
    while True:
        for url, name in SITES:
            try:
                html = fetch(url)
                links = extract_links(url, html)
                new_links = [l for l in links if l not in seen]
                if new_links and not first:
                    for l in new_links:
                        send_telegram(f"🆕 {name}\n{l}")
                seen.update(new_links)
            except Exception as e:
                print("Napaka:", e)
        save_seen(seen)
        first = False
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
