import logging
from urllib import response
import requests
import configparser
from jinja2 import Environment, FileSystemLoader, select_autoescape
from bmmbackend import bmmbackend
import sqlite3
import json

conn = sqlite3.connect("checked_items.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS checked_items (item_id TEXT PRIMARY KEY)")


def is_checked(item_id):
    c.execute("SELECT 1 FROM checked_items WHERE item_id = ?", (item_id,))
    return c.fetchone() is not None


def mark_checked(item_id):
    c.execute("INSERT OR IGNORE INTO checked_items (item_id) VALUES (?)", (item_id,))
    conn.commit()


config = configparser.ConfigParser()
config.read_file(open("config.ini"))
logging.basicConfig(
    filename=config["DEFAULT"]["logfile_name"],
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s | %(module)s.%(funcName)s line %(lineno)d: %(message)s",
)

logging.info("Kormanyscraper started")

backend = bmmbackend(config["DEFAULT"]["monitor_url"], config["DEFAULT"]["uuid"])
env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
contenttpl = env.get_template("content.html")

url = config["Download"]["url"]
params = {
    "limit_rows_on_page": 10,
    "limit_page": 0,
}

response = requests.get(url, params=params)
logging.info(response.url)

if response.status_code == 200:
    data = response.json()["data"]

events = backend.getEvents()

new_items = []
for item in data:
    key = item["uuid"] + ":" + item["visibleDate"]
    if not is_checked(key):
        new_items.append(item)
        mark_checked(key)

for event in events["data"]:
    try:
        selected_options = json.loads(event["selected_options"])
    except:
        selected_options = None
    if type(selected_options) is not dict:
        selected_options = None

    content = ""
    for item in new_items:
        if selected_options and 'Forrás' in selected_options and item['ministry']['name'] != selected_options['Forrás'] and selected_options['Forrás'] != 'all':
            continue
        if selected_options and 'Dokumentum típus' in selected_options and item['category']['name'] != selected_options['Dokumentum típus'] and selected_options['Dokumentum típus'] != 'all':
            continue

        if event["type"] == 1:
            pass
        else:
            title = item["name"]
            pageUrl = f'https://kormany.hu/dokumentumtar/{item["slug"]}'
            dlUrl = (
                f'https://kormany.hu/publicapi/document-library/{item["slug"]}/download'
            )
            res = [title, pageUrl, dlUrl]
            content = content + contenttpl.render(doc=res)

    if config["DEFAULT"]["donotnotify"] == "0":
        backend.notifyEvent(event["id"], content)
        logging.info(
            f"Notified: {event['id']} - {event['type']} - {event['parameters']}"
        )

conn.close()

logging.info("KozlonyScraper ready. Bye.")

print("Ready. Bye.")
