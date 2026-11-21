import os
import json
import re
import requests
from bs4 import BeautifulSoup

=====================================

CONFIGURATION

=====================================

URL = “https://testcisia.it/calendario.php?tolc=cents&lingua=inglese”

TOKEN = os.environ[“BOT_TOKEN”].strip()
CHAT_ID = os.environ[“CHAT_ID”].strip()

STATE_FILE = “state.json”
TEST_TELEGRAM = os.getenv(“TEST_TELEGRAM”, “false”).lower() == “true”

=====================================

TELEGRAM

=====================================

def send_telegram(message):

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
response = requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=20
)
if not response.ok:
    raise RuntimeError(
        f"Telegram HTTP {response.status_code}: {response.text}"
    )
result = response.json()
if not result.get("ok"):
    raise RuntimeError(f"Telegram error: {result}")

=====================================

GET CISIA SLOTS

=====================================

def get_slots():

response = requests.get(URL, timeout=30)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")
slots = {}
for row in soup.find_all("tr"):
    cells = [
        cell.get_text(" ", strip=True)
        for cell in row.find_all(["td", "th"])
    ]
    if len(cells) < 8:
        continue
    cells = cells[-8:]
    modality = cells[0]
    university = cells[1]
    city = cells[3]
    deadline = cells[4]
    seats_text = cells[5]
    status = cells[6]
    test_date = cells[7]
    if not re.search(r"\d{2}/\d{2}/\d{4}", test_date):
        continue
    match = re.search(r"\d+", seats_text)
    seats = int(match.group()) if match else 0
    available = (
        seats > 0
        or "POSTI DISPONIBILI" in status.upper()
    )
    key = "|".join([
        modality,
        university,
        city,
        deadline,
        test_date
    ])
    slots[key] = {
        "university": university,
        "city": city,
        "date": test_date,
        "seats": seats,
        "status": status,
        "available": available
    }
if not slots:
    raise RuntimeError(
        "Could not read CISIA calendar. "
        "Check whether the website structure has changed."
    )
return slots

=====================================

LOAD PREVIOUS STATE

=====================================

def load_previous_state():

if not os.path.exists(STATE_FILE):
    return None
with open(STATE_FILE, "r", encoding="utf-8") as f:
    previous = json.load(f)
if not isinstance(previous, dict):
    raise RuntimeError("Invalid state.json format")
return previous

=====================================

SAVE CURRENT STATE

=====================================

def save_state(current):

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(
        current,
        f,
        indent=2,
        ensure_ascii=False
    )

=====================================

MAIN MONITOR

=====================================

def main():

# Test Telegram
if TEST_TELEGRAM:
    send_telegram(
        "✅ CENT-S BOT TEST\n\n"
        "Telegram connection successful!\n"
        "Your CENT-S Slot Hunter is ready."
    )
    print("Telegram test message sent successfully.")
    return
# Get current CISIA data
current = get_slots()
print(f"Successfully checked {len(current)} slots.")
# Load previous data
previous = load_previous_state()
# First run: save baseline
if previous is None:
    save_state(current)
    print("First run: baseline state saved.")
    send_telegram(
        "✅ CENT-S MONITOR STARTED\n\n"
        "Baseline successfully saved.\n"
        "Monitoring is now active.\n"
        f"Total slots checked: {len(current)}\n"
        "Next check: approximately 5 minutes."
    )
    return
# Compare current and previous data
alerts_sent = 0
for key, slot in current.items():
    old = previous.get(key, {})
    newly_available = (
        slot["available"]
        and not old.get("available", False)
    )
    more_seats = (
        slot["seats"] > old.get("seats", 0)
        and slot["available"]
    )
    if newly_available or more_seats:
        message = (
            "🚨 CENT-S SLOT ALERT!\n\n"
            f"University: {slot['university']}\n"
            f"City: {slot['city']}\n"
            f"Test date: {slot['date']}\n"
            f"Available seats: {slot['seats']}\n"
            f"Status: {slot['status']}\n\n"
            "Check the official website:\n"
            f"{URL}"
        )
        send_telegram(message)
        alerts_sent += 1
        print(
            f"ALERT SENT: {slot['university']} "
            f"- {slot['date']}"
        )
# Save current state
save_state(current)
# Send monitoring update EVERY successful run
if alerts_sent == 0:
    send_telegram(
        "✅ CENT-S MONITOR UPDATE\n\n"
        "Monitoring completed successfully.\n"
        "No new available slots or additional seats detected.\n\n"
        f"Total slots checked: {len(current)}\n"
        "Next check: approximately 5 minutes."
    )
else:
    send_telegram(
        "📊 CENT-S MONITOR UPDATE\n\n"
        "Monitoring completed successfully.\n"
        f"New alerts sent: {alerts_sent}\n"
        f"Total slots checked: {len(current)}"
    )
print(f"Monitoring completed. Alerts sent: {alerts_sent}")

=====================================

RUN

=====================================

if name == “main”:
main()
