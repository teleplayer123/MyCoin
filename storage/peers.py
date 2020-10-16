import sqlite3
import os

from config import config

FILENAME = config["network"]["node_db"]

class Peers(object):

    def __init__(self, filename=None):
        self.filename = FILENAME if filename is None else filename
        create = not os.path.exists(self.filename)
        if create:
            if not os.path.exists("data"):
                os.mkdir("data")
            self.initDB()

    def initDB(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS peers ("
                        "host CHAR(100) NOT NULL, "
                        "downtime INTEGER NOT NULL,"
                        "PRIMARY KEY (host))")
            cursor.execute("INSERT INTO peers "
                        "(host, downtime)"
                        "VALUES (?, ?)",
                        ("127.0.0.1", 0))
            db.commit()


    def add_peer(self, host):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("INSERT OR IGNORE INTO peers"
                        "(host, downtime)"
                        "VALUES (?, ?)",
                        (host, 0))
            db.commit()
            return cursor.lastrowid

    def get_peer(self, host):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("SELECT host FROM peers WHERE host='{}'".format(host))
            return cursor.fetchone()

    def get_all_peers(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM peers")
            peers = cursor.fetchall()
            for peer in peers:
                yield peer

    def get_peer_downtime(self, host):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM peers WHERE host='{}'".format(host))
            downtime = cursor.fetchone()[1]
            return downtime

    def record_downtime(self, host):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor() 
            cursor.execute("UPDATE peers SET downtime=downtime+1 WHERE host='{}'".format(host))
            return 

    def remove_peer(self, host):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("DELETE * FROM peers WHERE host = {}".format(host))
            return 