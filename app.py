import os
import json
from flask import Flask
import requests
from bs4 import BeautifulSoup
import time
from threading import Thread
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
URL_TO_MONITOR = os.environ.get('URL_TO_MONITOR', 'https://pastebin.com/MCH7HhZ6')
TELEGRAM_BOT_TOKEN = '7913828575:AAGETnjPLPlNwMwE4uEgrS_2x6W8x9yvM3Q'
CHAT_ID = '-1002440867170'
CHECK_INTERVAL = 3  # Check every 3 seconds
COOKIE_FILE = 'cookies.json'  # Path to the JSON file containing cookies

last_content = None

def load_cookies():
    try:
        with open(COOKIE_FILE, 'r') as f:
            cookies = json.load(f)
            # Ensure all cookie values are strings
            for cookie in cookies.get('cookies', []):
                cookie['value'] = str(cookie['value'])
            return cookies
    except FileNotFoundError:
        logging.error(f"Cookie file {COOKIE_FILE} not found.")
        return None
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in cookie file {COOKIE_FILE}.")
        return None

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f"Telegram message sent: {message}")
    except requests.RequestException as e:
        logging.error(f"Failed to send Telegram message: {e}")

def normalize_content(content):
    # Remove extra whitespace and convert to lowercase
    return ' '.join(content.split()).lower()

def check_for_changes():
    global last_content
    cookies = load_cookies()
    if cookies is None:
        logging.error("Failed to load cookies. Skipping this check.")
        return

    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies.get('cookies', [])}

    try:
        response = requests.get(URL_TO_MONITOR, cookies=cookie_dict, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Use the provided selector to find the specific content
        target_content = soup.select_one("body > div.wrap > div.container > div.content > div.post-view.js-post-view")
        
        current_content = target_content.get_text() if target_content else ""
        normalized_current_content = normalize_content(current_content)

        if last_content is None:
            last_content = normalized_current_content
            logging.info('Initial content stored')
            send_telegram_message(f'Monitoring started for {URL_TO_MONITOR}. Initial content stored.')
        elif normalized_current_content != last_content:
            logging.info('Content changed')
            send_telegram_message(f'The webpage content has changed at {URL_TO_MONITOR}!')
            last_content = normalized_current_content
    except requests.RequestException as e:
        logging.error(f"Error fetching the webpage: {e}")
        send_telegram_message(f"Error monitoring {URL_TO_MONITOR}: {e}")

def monitoring_thread():
    while True:
        check_for_changes()
        time.sleep(CHECK_INTERVAL)

@app.route('/')
def index():
    return f"Monitoring is active for {URL_TO_MONITOR}!"

if __name__ == '__main__':
    logging.info(f"Starting monitoring for {URL_TO_MONITOR}")
    # Start the monitoring in a separate thread
    monitor_thread = Thread(target=monitoring_thread)
    monitor_thread.daemon = True
    monitor_thread.start()
    # Run the Flask app
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=6000)
