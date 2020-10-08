from flask import Flask, request, jsonify
import requests
import json
import logging
import ssl
import socket
import struct


from config import config


app = Flask(__name__)
host = config["network"]["host"]
port = config["network"]["port"]

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile="ca_certs/server.crt")
ctx.load_cert_chain("ca_certs/client.crt", "ca_certs/client.key")



@app.route("/status", methods=["GET"])
def check_status():
    return json.dumps(config["network"]), 200


@app.route("/connect", methods=["POST"])
def connect():
    addr = (config["network"]["shost"], config["network"]["sport"])
    body = request.get_json()
    peer = body["host"]
    network = body["network"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = ctx.wrap_socket(s, server_hostname="Cole")
        sock.connect(addr)
        if network == config["network"]:
            sock.send("PEER:{}".format(peer).encode())
            res = sock.recv(4096)
            logger.info(" Response: {}".format(res.decode()))
            if res == b"True":
                return json.dumps({"success": True}), 201 
            else:
                return json.dumps({"success": False}), 401
        else:
            sock.send("BADPEER:{}".format(peer).encode())
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