import requests
import json
import configparser

config = configparser.ConfigParser()
config.read_file(open("config.ini"))

with open("options_schema.json") as f:
    options_schema = json.load(f)

base_url = config["DEFAULT"]["monitor_url"]

url = f"{base_url}/api/eventgenerators"

data = {
    "name": "Kormány figyelő",
    "description": "Kormány figyelő scraper",
    "options_schema": options_schema,
}

response = requests.post(url, json=data)

print(response.status_code)
print(response.json())
