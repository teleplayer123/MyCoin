from flask import Flask, request, jsonify
import requests
import json
import logging
import ssl
import socket
import struct


from config import config
from tools.validation import allow_peer, blocked_host


app = Flask(__name__)
host = config["network"]["host"]
port = config["network"]["port"]

logging.basicConfig(filename="logs/proxy_server.log", level=logging.DEBUG)
logger = logging.getLogger("proxy")

ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile="ca_certs/server.crt")
ctx.load_cert_chain("ca_certs/client.crt", "ca_certs/client.key")



@app.route("/status", methods=["GET"])
def check_status():
    host = request.host.split(":")[0]
    if allow_peer(host):
        return json.dumps(config["network"]), 200
    else:
        return json.dumps({"message": "ACCESS DENIED"}), 400
        logger.warning(" {} Denied Access while requesting network status".format(host))


@app.route("/connect", methods=["POST"])
def connect():
    addr = (config["network"]["shost"], config["network"]["sport"])
    caddr = request.host.split(":")[0]
    if blocked_host(caddr):
        return json.dumps({"message": "ACCESS DENIED"}), 401
        logger.warning(" {} Denied Access while trying to connect to proxy".format(caddr))
    body = request.get_json()
    peer = body["host"]
    network = body["network"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = ctx.wrap_socket(s, server_hostname="Cole")
        sock.connect(addr)
        logger.info(" Connecting to {}".format(addr))
        if caddr != peer:
            sock.send("BADPEER:{}".format(peer).encode())
            return json.dumps({"success": False}), 401
        elif network == config["network"] and caddr == peer:
            sock.send("PEER:{}".format(peer).encode())
            res = sock.recv(4096)
            logger.info(" Response: {}".format(res.decode()))
            if res == b"True":
                return json.dumps({"success": True}), 201 
            else:
                return json.dumps({"success": False}), 401
    except socket.error as err:
        logger.error(" Socket Error: {}".format(err))
        if sock is not None:
            sock.close()
    finally:
        if sock is not None:
            sock.close()


@app.route("/transaction", methods=["POST"])
def post_unconfirmed():
    addr = (config["network"]["shost"], config["network"]["sport"])
    body = request.get_json() 
    trans = body["transaction"]
    type = body["type"]
    host = body["host"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = ctx.wrap_socket(s, server_hostname="Cole")
        sock.connect(addr)
        sock.send("TYPE:{}:HOST:{}:TRANS:{}".format(type, host, trans).encode())
        res = sock.recv(4096).decode()
        logger.debug(" {}".format(res))
        if res == "True":
            return json.dumps({"success": True}), 201
        else:
            return json.dumps({"success": False}), 401
    except socket.error as err:
        logger.error(" Socket Error: {}".format(err))
        if sock is not None:
            sock.close()
    finally:
        if sock is not None:
            sock.close()



def run():
    app.run(host, port)