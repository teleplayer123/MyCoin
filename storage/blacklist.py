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
                        "host CHAR(60) NOT NULL,"
                        "time CHAR(100) NOT NULL,"
                        "PRIMARY KEY (host))")
            db.commit()
    
    def blacklist_host(self, host, time):
        if host == "127.0.0.1":
            return False
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            if host in self.get_blacklisted():
                cursor.execute("UPDATE blacklist SET time='{}' WHERE host='{}'".format(time, host))
            else:
                cursor.execute("INSERT INTO blacklist "
                            "(host, time) "
                            "VALUES (?, ?)",
                            (host, time))
            db.commit()
        return True
    
    def get_blacklisted(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("SELECT host FROM blacklist")
            peers = cursor.fetchall()
            return [p[0] for p in peers]