import sqlite3
import os

from config import config
from wallet import Transaction


class Mempool(object):

    mempool_db = config["network"]["mempool_db"]

    def __init__(self):
        self.filename = self.mempool_db
        try:
            if not os.path.exists(os.path.dirname("data")):
                os.mkdir("data")
        except os.error:
            pass
        create = not os.path.exists(self.filename)
        if create:
            self.initDB()

    def initDB(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS unconfirmed_transactions ("
                        "public_address TEXT NOT NULL,"
                        "recipient TEXT NOT NULL,"
                        "amount INTEGER NOT NULL,"
                        "signature TEXT NOT NULL,"
                        "txt_hash TEXT NOT NULL,"
                        "timestamp INTEGER NOT NULL,"
                        "trans_id TEXT NOT NULL,"
                        "PRIMARY KEY (txt_hash)"
                        "UNIQUE (trans_id, timestamp) ON CONFLICT ROLLBACK) WITHOUT ROWID")
            db.commit()
        print(f"{self.filename} created")

    def add_unconfirmed_transaction(self, transaction):
        trans = Transaction.from_dict(transaction)
        trans_id = trans.hash
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO unconfirmed_transactions"
                        "(public_address, recipient, amount, signature, txt_hash, timestamp, trans_id)"
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (transaction["sender_address"], transaction["recipient_address"], transaction["amount"],
                        transaction["signature"], transaction["txt_hash"], transaction["timestamp"], trans_id))
            db.commit()

    def get_unconfirmed_transaction(self, txt_hash):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute(f"SELECT * FROM unconfirmed_transactions WHERE txt_hash='{txt_hash}'")
            data = cursor.fetchall()
            trans = data[0]
            return Transaction(trans[0], "", trans[1], trans[2], trans[3], trans[4], trans[5])

    def get_all_unconfirmed_transactions(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM unconfirmed_transactions")
            trans = cursor.fetchall()
            for t in trans:
                yield Transaction(t[0], "", t[1], t[2], t[3], t[4], t[5])

    def get_txt_hashes(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("SELECT txt_hash FROM unconfirmed_transactions")
            hashes = cursor.fetchall()
            return hashes

    def remove_unconfirmed_transaction(self, txt_hash):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute(f"DELETE * FROM unconfirmed_transactions WHERE txt_hash={txt_hash}")
            return

    def remove_unconfirmed_transactions(self):
        with sqlite3.connect(self.filename) as db:
            cursor = db.cursor()
            cursor.execute("DELETE FROM unconfirmed_transactions")
            return cursor.rowcount