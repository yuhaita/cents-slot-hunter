import os
import json
import re
import requests
from bs4 import BeautifulSoup

URL = "https://testcisia.it/calendario.php?tolc=cents&lingua=inglese"

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = "state.json"


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message
    }, timeout=20)
    response.raise_for_status()


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
            seats > 0 or
            "POSTI DISPONIBILI" in status.upper()
        )

        key = "|".join([
            modality, university, city,
            deadline, test_date
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
        raise RuntimeError("Could not read CISIA calendar")

    return slots


def main():
    current = get_slots()

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            previous = json.load(f)
    else:
        previous = None

    if previous is not None:
        for key, slot in current.items():
            old = previous.get(key, {})

            newly_available = (
                slot["available"] and
                not old.get("available", False)
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

    with open(STATE_FILE, "w") as f:
        json.dump(current, f, indent=2)

    print(f"Successfully checked {len(current)} slots.")


if __name__ == "__main__":
    main()
