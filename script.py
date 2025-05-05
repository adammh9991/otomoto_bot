import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
from twilio.rest import Client
import hashlib
import time

# === KONFIGURACJA ===
OTOMOTO_URL = "https://www.otomoto.pl/osobowe/toyota/yaris?search%5Bfilter_float_year%3Afrom%5D=2015"
CHECK_INTERVAL = 600  # sekundy

# Zmienne środowiskowe z Render
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_FROM = os.getenv("TWILIO_PHONE_FROM")
TWILIO_PHONE_TO = os.getenv("TWILIO_PHONE_TO")

# === FUNKCJE ===

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

def send_discord(message):
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})

def send_sms(message):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE_FROM,
        to=TWILIO_PHONE_TO
    )

def get_offers():
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(OTOMOTO_URL, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    offers = soup.select("article")
    result = []
    for offer in offers:
        title_tag = offer.select_one("h1, h2, h3")
        price_tag = offer.select_one("[data-testid='ad-price']") or offer.select_one(".ooa-1bmnxg7")
        link_tag = offer.select_one("a")

        title = title_tag.text.strip() if title_tag else "Brak tytułu"
        price = price_tag.text.strip() if price_tag else "Brak ceny"
        link = link_tag['href'] if link_tag and link_tag.has_attr('href') else ""
        if not link.startswith("http"):
            link = "https://www.otomoto.pl" + link

        result.append({"title": title, "price": price, "link": link})
    return result

def offers_hash(offers):
    ids = [offer['link'] for offer in offers]
    return hashlib.sha256("".join(sorted(ids)).encode()).hexdigest()

def main():
    last_hash = None

    while True:
        try:
            offers = get_offers()
            current_hash = offers_hash(offers)

            if current_hash != last_hash:
                print("🔔 Nowe oferty!")
                msg = "\n\n".join([f"{o['title']} — {o['price']}\n{o['link']}" for o in offers[:5]])
                send_email("Nowe oferty na Otomoto!", msg)
                send_discord(f"🚗 Nowe oferty:\n\n{msg}")
                send_sms("Nowe oferty na Otomoto! Sprawdź Discorda lub maila.")
                last_hash = current_hash
            else:
                print("Brak nowych ofert.")
        except Exception as e:
            print("❌ Błąd:", e)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
