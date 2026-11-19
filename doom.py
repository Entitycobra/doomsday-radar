import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

MOVIE_URL = "https://in.bookmyshow.com/movies/chennai/avengers-doomsday/ET00439706"
SHOWTIMES_URL = "https://in.bookmyshow.com/buytickets/avengers-doomsday-chennai/movie-chen-ET00439706-MT/20261217"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")

# Optional: Put specific Chennai theatres here if you ONLY want alerts for them
# Leave empty [] to get alerted for ANY open Chennai theatre
TARGET_THEATRES = []  # Example: ["sathyam", "palazzo", "luxe", "vr chennai", "ags"]

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
            "Actions": f"view, Book Tickets Now, {link}"
        },
        timeout=10
    )
    print("ALERT SENT TO PHONE!")

def check_bookings():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        page = context.new_page()

        try:
            # 1. Check the direct Chennai Avengers: Doomsday movie page
            page.goto(MOVIE_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)
            print("Page title:", page.title())

            body_text = page.inner_text("body").lower()
            if "just a moment" in body_text or "attention required" in body_text:
                print("Blocked by Cloudflare on this run. Will retry next cycle.")
                browser.close()
                return False, None

            # 2. Check the Dec 17 Chennai showtimes page for open theatres
            page.goto(SHOWTIMES_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)

            venue_links = page.locator("a[href*='/cinemas/chennai/']").all()
            open_theatres = []
            for v in venue_links:
                name = (v.inner_text() or "").strip()
                if name and name not in open_theatres:
                    open_theatres.append(name)

            print(f"Open Chennai theatres found ({len(open_theatres)}):", open_theatres)

            if TARGET_THEATRES:
                matched = [
                    t for t in open_theatres
                    if any(target.lower() in t.lower() for target in TARGET_THEATRES)
                ]
                browser.close()
                return (len(matched) > 0), matched

            # Fallback: check if "Book tickets" button is active on the main movie page
            book_btn_visible = "book tickets" in body_text
            browser.close()
            return (len(open_theatres) > 0 or book_btn_visible), open_theatres

        except Exception as e:
            print(f"Error checking page: {e}")
            browser.close()
            return False, None

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning Chennai theaters for Avengers: Doomsday...")
    is_open, theatres = check_bookings()

    if is_open:
        if theatres:
            preview = ", ".join(theatres[:5])
            msg = f"Open at {len(theatres)} Chennai theatre(s): {preview}. Tap to book!"
        else:
            msg = "Book Tickets button is LIVE for Chennai! Tap now to grab seats."

        send_phone_alert(
            "DOOMSDAY TICKETS LIVE IN CHENNAI!",
            msg,
            MOVIE_URL
        )
    else:
        print("Target theatres not open yet.")
