import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup

# ======= NASTAVITVE =======
INTERVAL_SECONDS = 60  # kako pogosto preverja (npr. 60, 120, 300 ...)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
SEEN_FILE = "seen.json"

SITES = [
    # (URL, oznaka)
    ("https://www.bolha.com/podarim", "Bolha - Podarim"),
    ("https://www.podarimo.si/podarim/vsi-oglasi/stran-1", "Podarimo.si - Podarim (stran 1)"),
]

# ======= POMOŽNE FUNKCIJE =======
def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_seen(seen):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(seen)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Manjka BOT_TOKEN ali CHAT_ID – preveri Environment Variables.")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
        requests.post(url, data=data, timeout=15)
    except Exception as e:
        print("Telegram error:", e)

def fetch(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=25)
    r.raise_for_status()
    return r.text

def absolutize(base_url, href):
    """Pretvori relativne linke v absolutne."""
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base_url)
        if m:
            return m.group(1) + href
    return href

def extract_items(url, html):
    """
    Vrne seznam (link, title) za oglase.
    - Na bolha.com sprejme SAMO /podarim oglase.
    - Na podarimo.si sprejme vse oglase (/oglas/).
    """
    soup = BeautifulSoup(html, "html.parser")
    found = []

    for a in soup.find_all("a", href=True):
        href_raw = a["href"]
        href = absolutize(url, href_raw)

        # --- BOLHA: strogo samo /podarim ---
        if "bolha.com" in href:
            # nujno mora biti v /podarim in kazati na oglas/oglasi
            if "/podarim" not in href:
                continue
            if not re.search(r"/oglas/|/oglasi/", href):
                continue
            title = a.get_text(" ", strip=True) or "Oglas"
            found.append((href.split("?")[0], title))
            continue

        # --- PODARIMO.SI: dovoli /oglas/ (posamezni oglasi) + znotraj /podarim/ ---
        if "podarimo.si" in href:
            if ("/oglas/" in href) or ("/podarim/" in href):
                title = a.get_text(" ", strip=True) or "Oglas"
                found.append((href.split("?")[0], title))
            continue

    # odstrani duplikate, ohrani prvi naslov
    uniq = []
    seen = set()
    for link, title in found:
        if link not in seen:
            seen.add(link)
            uniq.append((link, title))
    return uniq

# ======= GLAVNI LOOP =======
def main():
    seen = load_seen()
    first_run = len(seen) == 0  # prvi zagon: samo zabeleži trenutno stanje, ne pošiljaj notifikacij

    print(f"Začenjam. Že videnih: {len(seen)}. Prvi zagon: {first_run}")

    while True:
        try:
            for url, label in SITES:
                try:
                    html = fetch(url)
                    items = extract_items(url, html)  # list[(link, title)]
                    new_items = [(l, t) for (l, t) in items if l not in seen]

                    if new_items and not first_run:
                        for l, t in new_items:
                            send_telegram(f"🆕 {label}\n{t}\n{l}")

                    # zabeleži nove linke
                    for l, _ in new_items:
                        seen.add(l)
                except Exception as e:
                    print("Napaka pri obdelavi:", label, e)

            save_seen(seen)
            first_run = False

        except Exception as e:
            print("Napaka v glavni zanki:", e)

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
