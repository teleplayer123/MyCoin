import socket
import ssl
import json
import multiprocessing as mp
from time import localtime, time, sleep
from datetime import date

from blockchain import BlockChain
from miner import Miner
from storage.blacklist import BlackList
from storage.peers import Peers
from storage.binbc import BlockchainStorage
from storage.mempool import Mempool
from tools.utils import deserialize_trans_header
from tools.logger import Logger
from wallet import Transaction
from config import config

MAX_DOWNTIME = config["network"]["max_downtime"]
MAX_TRANSACTIONS = config["network"]["max_transactions"]
HOST = config["network"]["shost"]
PORT = config["network"]["sport"]

l = Logger("main", "base_server.log")
logger = l.get_logger()

class BaseServer(object):

    def __init__(self):
        self.peers = Peers()
        self.blacklist = BlackList()
        self.blockchain = BlockChain()
        self.storage = BlockchainStorage()
        self.mempool = Mempool()
        self.miner = Miner()

        self.ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.ctx.load_cert_chain("ca_certs/server.crt", "ca_certs/server.key")
        self.ctx.load_verify_locations("ca_certs/client.crt")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, PORT))
        self.sock.listen(1)
        logger.info(" Listening on {}:{}".format(HOST, PORT))
        
    def plisten(self):
        trys = 0
        try:
            while True:
                try:
                    ssock, caddr = self.sock.accept()
                    if caddr[0] in self.blacklist.get_blacklisted():
                        logger.warning(" Blacklisted host {} attempt to connect at {}".format(caddr[0], self.get_time()))
                        ssock.close()
                        continue
                    elif caddr[0] in [p for p in self.peers.get_all_peers()] and self.peers.get_peer_downtime(caddr[0]) > MAX_DOWNTIME:
                        self.remove_and_blacklist(caddr[0])
                        ssock.close()
                        continue
                    elif trys > 2:
                        tm_str = self.get_time()
                        flag = self.blacklist.blacklist_host(caddr[0], tm_str)
                        if flag == False:
                            logger.warning(" Cannot blacklist local host")
                        else:
                            logger.warning(" {} has been blacklisted at {} -- trys: {}".format(caddr[0], tm_str, trys))
                        ssock.close()
                        trys = 0
                        continue
                    else:
                        csock = self.ctx.wrap_socket(ssock, server_side=True)
                        logger.info(" accpting connection from {}".format(caddr))
                        self.proc = mp.Process(target=self.handler(csock))
                        self.proc.start()
                except socket.error as err:
                    logger.error("Socket Error: {}".format(err))
                    trys += 1
                    if self.peers.get_peer(caddr[0]) != None and caddr[0] != "127.0.0.1":
                        self.peers.record_downtime(caddr[0])
                        logger.warning(" {} downtime: {}".format(caddr[0], self.peers.get_peer_downtime(caddr[0])))
                    else:
                        logger.warning(" Host: {} Failed attempts: {}".format(caddr[0], trys))
                except KeyboardInterrupt:
                    break
        except KeyboardInterrupt:
            if self.sock is not None:
                self.sock.close()
                logger.debug(" Main socket closed")
            if csock is not None:
                csock.close()
                logger.debug(" Client socket closed")
            if self.proc is not None:
                self.proc.terminate()
                logger.debug(" Closing process")

    def handler(self, csock):
        data = ""
        while True:
            res = csock.recv(1024).decode()
            data += res
            if len(res) < 1024:
                break
        if data.split(":")[0] == "PEER":
            flag = self.connect_peer(data.split(":")[1])
        elif data.split(":")[0] == "BADPEER":
            flag = self.remove_and_blacklist(data.split(":")[1])
        elif data.split(":")[0] == "TYPE" and data.split(":")[1] == "unconfirmed":
            host = data.split(":")[3]
            trans = deserialize_trans_header(data.split(":")[5])
            flag = self.add_unconfirmed_trans(host, trans)
        else:
            flag = False
        csock.send("{}".format(flag).encode())

    def get_time(self):
        d = date.today()
        t = localtime(time())
        return "{} {}:{}:{}".format(d, t.tm_hour, t.tm_min, t.tm_sec)

    def remove_and_blacklist(self, *peers):
        tm_str = self.get_time()
        for peer in peers:
            if peer in [i[0] for i in self.peers.get_all_peers()]:
                self.peers.remove_peer(peer)
                logger.warning(" {} removed from peers".format(peer))
            flag = self.blacklist.blacklist_host(peer, tm_str)
            if flag == False:
                logger.warning(" Cannot blacklist localhost")
            else:
                logger.warning(" {} has been blacklisted".format(peer))
        return False

    def connect_peer(self, peer):
        all_peers = [i[0] for i in self.peers.get_all_peers()]
        if peer in self.blacklist.get_blacklisted():
            logger.warning(" Blacklisted host: {} connection attempt at {}".format(peer, localtime(time())))
            return False
        elif peer in all_peers:
            if self.peers.get_peer_downtime(peer) > MAX_DOWNTIME:
                self.remove_and_blacklist(peer)
                return False
            else:
                logger.info(" {} already in peers".format(peer))
                return True
        elif peer not in all_peers:
            self.peers.add_peer(peer)
            logger.info(" {} added to peers".format(peer))
            return True

    def add_unconfirmed_trans(self, host, trans):
        if host not in [p[0] for p in self.peers.get_all_peers()]:
            logger.warning(" POST UTX error, {} not in peers".format(host))
            return False
        trans_from_dic = Transaction.from_dict(trans)
        valid = self.blockchain.verify_transaction(trans["sender_address"], trans["recipient_address"], 
                                                trans["signature"], trans["amount"])
        if valid and trans_from_dic.txt_hash == trans["txt_hash"]:
            self.mempool.add_unconfirmed_transaction(trans)
            logger.info(" Unconfirmed Tx {} verified, added to mempool".format(trans_from_dic.txt_hash))
            if len([t for t in self.mempool.get_all_unconfirmed_transactions()]) >= MAX_TRANSACTIONS:
                self.miner.start()
                logger.debug(" Mining process starting")
                if len([t for t in self.mempool.get_all_unconfirmed_transactions()]) == 0:
                    logger.debug(" Mining process finished")
                else:
                    sleep(5)
            return True
        else:
            logger.warning(" Invalid Transaction: {}".format(trans_from_dic.txt_hash))
            return False