import sqlite3
import os
import json
import re
import math

from config import config

FH = config["user"]["user_pool"]

class PasswordPool(object):

    def __init__(self, filename=None):
        self.filename = FH if filename is None else filename
        if not os.path.exists(self.filename):
            self.db_init()

    def db_init(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS user_data ("
                        "username CHAR(32) NOT NULL, " 
                        "ciphertext TEXT NOT NULL, "
                        "tag CHAR(16) NOT NULL, "
                        "nonce CHAR(16) NOT NULL, "
                        "secret_question CHAR(32) NOT NULL, "
                        "key CHAR(16) NOT NULL, "
                        "PRIMARY KEY (username)) WITHOUT ROWID")
            db.commit()
        return

    def store_data(self, username, secret_question, key, json_data):
        data = json.loads(json_data)
        ciphertext = data["ciphertext"]
        tag = data["tag"]
        nonce = data["nonce"]
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO user_data "
                        "(username, ciphertext, tag, nonce, secret_question, key)"
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (username, ciphertext, tag, nonce, secret_question, key))
            db.commit()

    def get_user_data(self, username=None):
        if username is None:
            raise ValueError("error, no username")
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM user_data WHERE username='{}'".format(username))
            items = cursor.fetchall()
            data = items[0]
        return data[0], data[1], data[2], data[3], data[4], data[5]


def password_strength(password):
    n = math.log(len(set(password)))
    nums = re.search("[0-9]", password) is not None and re.match("^[0-9]*$", password) is None
    caps = password != password.upper() and password != password.lower()
    symbols = re.match("^[a-zA-Z0-9]*$", password) is None
    score = len(password) * (n + nums + caps + symbols)/20
    print(int(nums), int(caps), int(symbols))
    strength = {0:"weak", 1: "medium", 2: "strong"}
    return strength[int(score)]
