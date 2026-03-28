#!/usr/bin/env python3
"""
A Levels Results Monitor for Sri Lanka (doenets.lk)
Monitors examDetails API for any change and sends:
- Email notification
- Twilio SMS + Phone Call
- Telegram Bot message
"""
import os
import requests
import hashlib
import time
import smtplib
import asyncio
import telegram
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from twilio.rest import Client


class ResultsMonitor:
    def __init__(
        self,
        email_address=None,
        email_password=None,
        check_interval=10,
        twilio_sid=None,
        twilio_token=None,
        twilio_from=None,
        twilio_to=None,
        telegram_token=None,
        telegram_chat_ids=None,
    ):

        self.monitor_url = os.environ.get("MONITOR_URL", "https://result.doenets.lk/result/service/examDetails")
        self.email_address = email_address
        self.email_password = email_password
        self.check_interval = check_interval
        self.hash_file = Path("exam_hash.txt")
        self.log_file = Path("monitor_log.txt")

        self.twilio_sid = twilio_sid
        self.twilio_token = twilio_token
        self.twilio_from = twilio_from
        self.twilio_to = twilio_to

        self.telegram_token = telegram_token
        self.telegram_chat_ids = telegram_chat_ids or []

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    # ─── LOGGING ──────────────────────────────────────────────
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")

    # ─── HASHING ──────────────────────────────────────────────
    def fetch(self):
        try:
            response = self.session.get(self.monitor_url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            self.log(f"ERROR fetching page: {e}")
            return None

    def get_hash(self, content):
        return hashlib.md5(content.encode()).hexdigest()

    def load_hash(self):
        if self.hash_file.exists():
            return self.hash_file.read_text().strip()
        return None

    def save_hash(self, hash_value):
        self.hash_file.write_text(hash_value)

    # ─── EMAIL ────────────────────────────────────────────────
    def send_email(self):
        if not self.email_address or not self.email_password:
            self.log("Email credentials not set. Skipping.")
            return
        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(self.email_address, self.email_password)
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = self.email_address
            msg["Subject"] = "ALERT: A Levels Results Update - doenets.lk"
            msg.attach(
                MIMEText(
                    f"The results page has changed!\n\n"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Check now: https://doenets.lk/examresults",
                    "plain",
                )
            )
            server.send_message(msg)
            server.quit()
            self.log("Email sent!")
        except Exception as e:
            self.log(f"Email error: {e}")

    # ─── TWILIO ───────────────────────────────────────────────
    def send_twilio(self):
        if not all(
            [self.twilio_sid, self.twilio_token, self.twilio_from, self.twilio_to]
        ):
            self.log("Twilio credentials not set. Skipping.")
            return
        try:
            client = Client(self.twilio_sid, self.twilio_token)

            client.messages.create(
                body="ALERT! Your A Levels results page has changed! Check doenets.lk now!",
                from_=self.twilio_from,
                to=self.twilio_to,
            )
            self.log("Twilio SMS sent!")

            client.calls.create(
                twiml="<Response>"
                '<Say voice="alice">Alert! Your A Levels results have been released!</Say>'
                '<Pause length="1"/>'
                '<Say voice="alice">Please check the website d o e nets dot l k immediately!</Say>'
                '<Pause length="1"/>'
                '<Say voice="alice">Good luck!</Say>'
                "</Response>",
                from_=self.twilio_from,
                to=self.twilio_to,
            )
            self.log("Twilio call initiated!")

        except Exception as e:
            self.log(f"Twilio error: {e}")

    # ─── TELEGRAM ─────────────────────────────────────────────
    async def send_telegram_async(self):
        bot = telegram.Bot(token=self.telegram_token)
        for chat_id in self.telegram_chat_ids:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "🎉 ALERT! A Levels Results Update!\n\n"
                        "The results page on doenets.lk has changed!\n\n"
                        "Check now: https://doenets.lk/examresults"
                    ),
                )
                self.log(f"Telegram message sent to {chat_id}")
            except Exception as e:
                self.log(f"Telegram error for {chat_id}: {e}")

    def send_telegram(self):
        if not self.telegram_token or not self.telegram_chat_ids:
            self.log("Telegram credentials not set. Skipping.")
            return
        asyncio.run(self.send_telegram_async())

    # ─── NOTIFY ALL ───────────────────────────────────────────
    def notify_all(self):
        self.log("CHANGE DETECTED! Sending all notifications...")
        self.send_email()
        self.send_twilio()
        self.send_telegram()

    # ─── MAIN CHECK ───────────────────────────────────────────
    def check(self):
        self.log(f"Checking: {self.monitor_url}")
        content = self.fetch()
        if content is None:
            return

        current_hash = self.get_hash(content)
        last_hash = self.load_hash()

        if last_hash is None:
            self.save_hash(current_hash)
            self.log("Initial hash saved. Monitoring started.")
            return

        if current_hash != last_hash:
            self.save_hash(current_hash)
            self.notify_all()
        else:
            self.log("No changes detected.")

    # ─── MAIN LOOP ────────────────────────────────────────────
    def run_continuous(self):
        self.log("=" * 60)
        self.log("A Levels Results Monitor Started")
        self.log(f"Monitoring: {self.monitor_url}")
        self.log(f"Check interval: {self.check_interval} seconds")
        self.log("=" * 60)

        try:
            while True:
                self.check()
                self.log(f"Next check in {self.check_interval} seconds...")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.log("Monitor stopped by user.")
        except Exception as e:
            self.log(f"Unexpected error: {e}")


def main():
    # ===== CONFIGURATION - FILL THESE IN =====

    # ################
    YOUR_EMAIL = os.environ.get("EMAIL")
    YOUR_APP_PASSWORD = os.environ.get("EMAIL_PASSWORD")

    TWILIO_SID = os.environ.get("TWILIO_SID")
    TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN")
    TWILIO_FROM = os.environ.get("TWILIO_FROM")
    TWILIO_TO = os.environ.get("TWILIO_TO")

    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_IDS = [
        "6790516679",  # Bathila (you)
        "6121720038",  # Amadi Numaya
        "7500606290",  # 🥷 (Hellouworld221)
        "1559504928",  # Anusha Pabasara nejan
        "8537039647",  # Vinuth
        "8221258453",  # kushan
    ]
    #####################

    CHECK_INTERVAL = 10  # 10 seconds

    # ===== END CONFIGURATION =====

    monitor = ResultsMonitor(
        email_address=YOUR_EMAIL,
        email_password=YOUR_APP_PASSWORD,
        check_interval=CHECK_INTERVAL,
        twilio_sid=TWILIO_SID,
        twilio_token=TWILIO_TOKEN,
        twilio_from=TWILIO_FROM,
        twilio_to=TWILIO_TO,
        telegram_token=TELEGRAM_BOT_TOKEN,
        telegram_chat_ids=TELEGRAM_CHAT_IDS,
    )

    monitor.run_continuous()


if __name__ == "__main__":
    main()
