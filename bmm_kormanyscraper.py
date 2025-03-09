import logging
from typing import Optional
from urllib import response
import requests
import configparser
from jinja2 import Environment, FileSystemLoader, select_autoescape
from bmmbackend import bmmbackend
import sqlite3
import json
from bs4 import BeautifulSoup
import zipfile
import os
import re
import pdfplumber
from difflib import SequenceMatcher
from bmmtools import lemmatize

ID_SOURCE = "1"
ID_TYPE = "2"

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

if config["DEFAULT"]["donotlemmatize"] == "0":
    import huspacy

    nlp = huspacy.load()
else:
    nlp = None

logging.info("Kormanyscraper started")

backend = bmmbackend(config["DEFAULT"]["monitor_url"], config["DEFAULT"]["uuid"])
env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
contenttpl = env.get_template("content.html")
contenttpl_keyword = env.get_template("content_keyword.html")

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

doctext_by_uuid = {}
for item in new_items:
    logging.info(f"New item: {item['name']}")
    zip_url = f"https://kormany.hu/publicapi/document-library/{item['slug']}/download"
    response = requests.get(zip_url)
    if response.status_code == 200:
        # save zip
        with open(f"downloads/{item['slug']}.zip", "wb") as f:
            f.write(response.content)
        # extract zip
        with zipfile.ZipFile(f"downloads/{item['slug']}.zip", "r") as zip_ref:
            zip_ref.extractall(f"downloads/{item['slug']}")
        # clean up zip
        os.remove(f"downloads/{item['slug']}.zip")
    doctexts = {}
    for root, dirs, files in os.walk(f"downloads/{item['slug']}"):
        for file in files:
            if file.endswith(".pdf"):
                pdf_file = os.path.join(root, file)
                with pdfplumber.open(pdf_file) as pdf:
                    texts = ""
                    for page in pdf.pages:
                        texts += page.extract_text() + "\n"
                    texts = texts.replace("\n", " ").replace("  ", " ").strip()
                    doctexts[file] = texts
    # clean up folder
    for root, dirs, files in os.walk(f"downloads/{item['slug']}"):
        for file in files:
            os.remove(os.path.join(root, file))
    os.rmdir(f"downloads/{item['slug']}")
    doctext_by_uuid[item["uuid"]] = doctexts

doctext_by_uuid_lemma = {}
if nlp:
    for uuid in doctext_by_uuid:
        doctext_by_uuid_lemma[uuid] = {}
        for file in doctext_by_uuid[uuid]:
            doctext_by_uuid_lemma[uuid][file] = lemmatize(
                nlp, doctext_by_uuid[uuid][file]
            )


def search(text, keyword, nlp_warn=False):
    results = []
    matches = [m.start() for m in re.finditer(re.escape(keyword), text, re.IGNORECASE)]

    words = text.split()

    for match_index in matches:
        # Convert character index to word index
        char_count = 0
        word_index = 0

        for word_index, word in enumerate(words):
            char_count += len(word) + 1  # +1 accounts for spaces
            if char_count > match_index:
                break

        # Get surrounding 10 words before and after the match
        before = " ".join(words[max(word_index - 16, 0) : word_index])
        after = " ".join(words[word_index + 1 : word_index + 17])
        found_word = words[word_index]
        match = SequenceMatcher(
            None, found_word, event["parameters"]
        ).find_longest_match()
        match_before = found_word[: match.a]
        if match_before != "":
            before = before + " " + match_before
        else:
            before = before + " "
        match_after = found_word[match.a + match.size :]
        if match_after != "":
            after = match_after + " " + after
        else:
            after = " " + after
        common_part = found_word[match.a : match.a + match.size]

        if nlp_warn:
            before = "szótövezett találat: " + before

        results.append(
            {
                "file": file,
                "before": before,
                "after": after,
                "common": common_part,
            }
        )
    return results


for event in events["data"]:
    try:
        selected_options: Optional[dict[list, str]] = json.loads(
            event["selected_options"]
        )
    except:
        selected_options = None
    if type(selected_options) is not dict:
        selected_options = None

    items_lengths = 0
    content = ""
    for item in new_items:
        if (
            selected_options
            and ID_SOURCE in selected_options
            and selected_options[ID_SOURCE]
            and item["ministry"]["name"] not in selected_options[ID_SOURCE]
        ):
            continue
        if (
            selected_options
            and ID_TYPE in selected_options
            and selected_options[ID_TYPE]
            and item["category"]["name"] not in selected_options[ID_TYPE]
        ):
            continue

        title = item["name"]
        pageUrl = f'https://kormany.hu/dokumentumtar/{item["slug"]}'
        dlUrl = f'https://kormany.hu/publicapi/document-library/{item["slug"]}/download'
        source = item["ministry"]["name"]
        doc_type = item["category"]["name"]
        leadHtml = item["lead"]
        if leadHtml is None:
            lead = ""
        else:
            leadSoup = BeautifulSoup(leadHtml, "html.parser")
            lead = leadSoup.get_text()
        visible_date = item["visibleDate"].replace("-", ". ") + "."

        if event["type"] == 1 and event["parameters"]:
            results = []
            for file in doctext_by_uuid[item["uuid"]]:
                text = doctext_by_uuid[item["uuid"]][file]
                current_results = search(text, event["parameters"])
                if not current_results and nlp:
                    current_results = search(
                        " ".join(doctext_by_uuid_lemma[item["uuid"]][file]),
                        event["parameters"],
                        nlp_warn=True,
                    )
                results.extend(current_results)

            res = {
                "source": source,
                "title": title,
                "lead": lead,
                "pageUrl": pageUrl,
                "dlUrl": dlUrl,
                "doc_type": doc_type,
                "visible_date": visible_date,
                "results": results[:5],
                "results_count": len(results),
                "keyword": event["parameters"],
            }
            if len(results) > 0:
                content = content + contenttpl_keyword.render(doc=res)
                items_lengths += 1
        else:
            res = {
                "source": source,
                "title": title,
                "lead": lead,
                "pageUrl": pageUrl,
                "dlUrl": dlUrl,
                "doc_type": doc_type,
                "visible_date": visible_date,
            }
            content = content + contenttpl.render(doc=res)
            items_lengths += 1

    if items_lengths > 1:
        content = "Találatok száma: " + str(items_lengths) + "<br>" + content

    if config["DEFAULT"]["donotnotify"] == "0" and items_lengths > 0:
        backend.notifyEvent(event["id"], content)
        logging.info(
            f"Notified: {event['id']} - {event['type']} - {event['parameters']}"
        )

conn.close()

logging.info("KozlonyScraper ready. Bye.")

print("Ready. Bye.")
