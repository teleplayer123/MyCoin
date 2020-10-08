import requests
import json
import logging
import socket
import struct

from tools.utils import serialize_trans_header
from config import config

port = config["network"]["port"]
saddr = (config["network"]["shost"], config["network"]["sport"])

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Client(object):

    def __init__(self, peers):
        self.peers = peers
        self.connect_url = config["network"]["connect_url"]
        self.max_peers = config["network"]["max_peers"]
        self.nodes_url = config["network"]["nodes_url"]
        self.status_url = config["network"]["status_url"]
        self.transaction_url = config["network"]["transaction_url"]

        host_name = socket.gethostbyname(socket.gethostname())
        if host_name not in [p for p in self.peers.get_all_peers()]:
            self.connect_peer(host_name)

    def get_nodes(self, host):
        url = self.nodes_url.format(host, port)
        try:
            response = requests.get(url)
            peers = response.json()
            if response.status_code == 200:
                return peers["nodes"]
        except requests.exceptions.RequestException:
            self.peers.record_downtime(host)


    def connect_peer(self, host):
        connect = self.connect_url.format(host, port)
        data = {
            "host": host,
            "network": config["network"]
        }
        try:
            res = requests.post(connect, json=data)
            logger.info(" response: {}".format(res.text))
        except requests.exceptions.RequestException:
            self.peers.record_downtime(host)
         

    def broadcast_unconfirmed_transaction(self, transaction):
        for node in self.peers.get_all_peers():    
            url = self.transaction_url.format(node[0], port)
            data = {
                "host": node[0],
                "type": "unconfirmed",
                "transaction": serialize_trans_header(transaction)
            }
            try: 
                response = requests.post(url, json=data)
                return response
            except requests.exceptions.RequestException:
                self.peers.record_downtime(node[0])
