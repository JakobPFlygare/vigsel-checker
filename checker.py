import urllib.request
import urllib.parse
import re
import os
from datetime import datetime, timezone, timedelta

SWEDISH_TZ = timezone(timedelta(hours=2))  # CEST (UTC+2), valid for September

TARGET_DATES = ["5 september 2026", "12 september 2026"]
MAIN_URL = "https://etjanster.stockholm.se/BokaVigsel/"
LAST_NOTIFIED_FILE = "last_notified.txt"


def fetch_page():
    req = urllib.request.Request(MAIN_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")


def find_available_targets(html):
    available = []
    slots = re.split(r'<div class="mt-2 bg-grey-lighter p-4">', html)[1:]
    for slot in slots:
        date_match = re.search(r'<h4[^>]*>([^<]+)</h4>', slot)
        status_match = re.search(r'"text":"(Lediga tider|Fullbokat)"', slot)
        if not date_match or not status_match:
            continue
        date_text = date_match.group(1).strip().lower()
        status = status_match.group(1)
        for target in TARGET_DATES:
            if target.lower() == date_text and status == "Lediga tider":
                available.append(target)
    return available


def load_last_notified():
    if os.path.exists(LAST_NOTIFIED_FILE):
        with open(LAST_NOTIFIED_FILE) as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def save_last_notified(dates):
    with open(LAST_NOTIFIED_FILE, "w") as f:
        for d in sorted(dates):
            f.write(d + "\n")


def send_whatsapp(message):
    phone = os.environ["CALLMEBOT_PHONE"]
    key = os.environ["CALLMEBOT_KEY"]
    encoded = urllib.parse.quote(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded}&apikey={key}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("Notification sent, status:", resp.status)


def is_night():
    now = datetime.now(SWEDISH_TZ)
    return now.hour < 7 or (now.hour == 7 and now.minute < 30)


def main():
    if os.environ.get("TEST_MODE") == "true":
        print("Test mode — sending test WhatsApp message.")
        send_whatsapp("Vigsel checker is working! This is a test message.")
        return

    if is_night():
        print("Nighttime in Sweden, skipping.")
        return

    try:
        html = fetch_page()
    except Exception as e:
        print(f"Fetch failed: {e}")
        return

    available = find_available_targets(html)

    if not available:
        print("No available target dates found.")
        return

    print(f"Available: {available}")

    last = load_last_notified()
    new = [d for d in available if d not in last]

    if not new:
        print("Already notified about these dates, skipping.")
        return

    message = "Vigsel slot open! Book now: " + ", ".join(new)
    try:
        send_whatsapp(message)
        save_last_notified(set(available))
    except Exception as e:
        print(f"Notification failed: {e}")


if __name__ == "__main__":
    main()
