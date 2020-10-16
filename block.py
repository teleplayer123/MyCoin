import binascii
import hashlib
import json
import shelve
from time import time

from wallet import Transaction
from config import config
from tools.utils import int_to_hex, hex_to_int

VERSION = config["network"]["version"]

class BlockHeader(object):

    def __init__(self, index, previous_hash, bits, difficulty, merkle_root, timestamp=None, proof=0, version=0):
        self.index = index
        self.previous_hash = previous_hash
        self.bits = bits
        self.difficulty = int(difficulty)
        self.merkle_root = merkle_root 
        self.timestamp = int(time()) if timestamp is None else int(timestamp)
        self.proof = int(proof)
        self.version = VERSION if version == 0 else version
        
    def to_hashable(self):
        return ("{0:0>10x}".format(self.index) +
        f"{self.previous_hash}" +
        "{0:08x}".format(self.bits) +
        "{0:08x}".format(int(self.difficulty)) +
        f"{self.merkle_root}" +
        "{0:08x}".format(self.timestamp) +
        "{0:08x}".format(self.proof) +
        "{0:08x}".format(self.version))

    @property
    def hash(self):
        hashable = self.to_hashable().encode("utf8")
        hash_obj = hashlib.pbkdf2_hmac("sha256", hashable, hashable, 1000, 32)
        return binascii.hexlify(hash_obj).decode("utf8")

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, block_dict):
        return cls(
                block_dict["index"],
                block_dict["previous_hash"], 
                block_dict["bits"],
                block_dict["difficulty"],
                block_dict["merkle_root"],
                block_dict["timestamp"],
                block_dict["proof"],
                block_dict["version"])

    def to_json(self):
        return json.dumps(self, default=lambda x: {k: v for k, v in x.__dict__.items()},
                sort_keys=True)

class Block(object):

    def __init__(self, index, previous_hash, bits, difficulty, transactions, merkle_root=None, timestamp=None, proof=0, version=0):
        self.index = index
        self.transactions = transactions
        _merkle_root = self.calculate_merkle_root() if merkle_root is None else merkle_root
        self.block_header = BlockHeader(self.index, previous_hash, bits, difficulty, _merkle_root, timestamp, proof, version)

    def calculate_merkle_root(self):
        if len(self.transactions) < 1:
            raise IndexError("zero transactions")
        base = [t.txt_hash.encode() for t in self.transactions]
        while len(base) > 1:
            root = []
            for i in range(0, len(base), 2):
                if i == len(base) - 1:
                    root.append(hashlib.sha256(base[i] + base[i]).hexdigest())
                else:
                    root.append(hashlib.sha256(base[i] + base[i+1]).hexdigest())
            base = [t.encode() for t in root]
        return base[0].decode()

    def to_dict(self):
        dic = {}
        for key, val in self.__dict__.items():
            if isinstance(val, list):
                dic[key] = [v.to_dict() for v in val]
            elif hasattr(val, "to_dict"):
                dic[key] = val.to_dict()
            else:
                dic[key] = val
        return dic

    @classmethod
    def from_dict(cls, block_dict):
        return cls(
            block_dict["index"],
            block_dict["block_header"]["previous_hash"],
            block_dict["block_header"]["bits"],
            block_dict["block_header"]["difficulty"],
            [Transaction(
                transaction["sender_address"],
                "",
                transaction["recipient_address"],
                transaction["amount"],
                signature=transaction["signature"],
                txt_hash=transaction["txt_hash"]
            )  for transaction in block_dict["transactions"]],
            block_dict["block_header"]["merkle_root"],
            block_dict["block_header"]["timestamp"],
            block_dict["block_header"]["proof"],
            block_dict["block_header"]["version"])