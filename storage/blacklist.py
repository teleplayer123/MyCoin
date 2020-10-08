import sqlite3
import os

FILENAME = "data/blacklist.sql"

class BlackList(object):

    def __init__(self):
        self.filename = FILENAME
        if not os.path.exists(self.filename):
            self.initDB()

    def initDB(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS blacklist ("
                        "host CHAR(60) NOT NULL, "
                        "PRIMARY KEY (host))")
            db.commit()
    
    def blacklist_host(self, host):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO blacklist "
                        "(host) "
                        "VALUES (?)",
                        (host))
            db.commit()
        return cursor.lastrowid
    
    def get_blacklisted(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("SELECT host FROM blacklist")
            peers = cursor.fetchall()
            return [p for p in peers]