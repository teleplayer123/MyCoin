from services.client import Client
from storage.peers import Peers
from config import config

import requests

conn_url = config["network"]["connect_url"].format("127.0.2.1", 6000)
res = requests.post(conn_url, json={"network": config["network"], "host": "192.168.56.101"})
print(res)