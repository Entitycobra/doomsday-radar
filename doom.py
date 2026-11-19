import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

MOVIE_KEYWORDS = ["avengers: doomsday", "avengers doomsday", "doomsday"]
CITY_URL = "https://in.bookmyshow.com/explore/movies-chennai"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")

def send_phone_alert(title, message, link):
    if not NTFY_TOPIC:
        print("Error: NTFY_TOPIC secret is not set.")
        return
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "urgent",
            "Tags": "rotating_light,ticket",
            "Click": link,
            "Actions": f"view, Open BookMyShow, {link}"
        },
        timeout=10
    )
    print("ALERT SENT TO PHONE!")

def check_bookings():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto(CITY_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            page_text = page.inner_text("body").lower()

            for keyword in MOVIE_KEYWORDS:
                if keyword in page_text:
                    for link in page.locator("a").all():
                        href = link.get_attribute("href") or ""
                        text = (link.inner_text() or "").lower()
                        if "doomsday" in text and "/buytickets/" in href:
                            full_url = f"https://in.bookmyshow.com{href}" if href.startswith("/") else href
                            browser.close()
                            return True, full_url

            browser.close()
            return False, None
        except Exception as e:
            print(f"Error checking page: {e}")
            browser.close()
            return False, None

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning Chennai listings...")
    is_open, booking_link = check_bookings()

    if is_open:
        send_phone_alert(
            "DOOMSDAY BOOKINGS OPEN IN CHENNAI!",
            "Tickets are live! Tap now to grab IMAX/SPI/PVR seats.",
            booking_link
        )
    else:
        print("Not open yet.")