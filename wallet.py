from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
import Crypto.Random
import base64
import json
import hashlib
import getpass
import os
import platform
from time import time
from socket import gethostname
import stat

from config import config
from tools.bcrypt_alg import bcrypt_encrypt, bcrypt_validate
from tools.encrypt_decrypt import encrypt, decrypt

class WalletError(Exception): 
    def __str__(self):
        return "Cannot make new wallet."    

class VerifyPasswordError(Exception):
    def __str__(self):
        return "Passwords do not match"

class LoadError(Exception):
    def __str__(self):
        return "Error while loading keys"


class Transaction(object):

    def __init__(self, public_address, private_key, recipient_address, amount, signature=None, txt_hash=None, timestamp=None):
        self.sender_address = public_address
        self.__private_key = private_key
        self.recipient_address = recipient_address
        self.amount = amount
        self.signature = self.__sign(self.pub_trans()) if signature is None else signature
        self.txt_hash = self.__calculate_txt_hash() if txt_hash is None else txt_hash
        self.timestamp = int(time()) if timestamp is None else timestamp

    def __to_hashable(self):
        return (self.sender_address +
            self.recipient_address +
            f"{self.amount}" +
            self.signature +
            f"{self.txt_hash}" +
            f"{self.timestamp}")
        
    @property
    def hash(self):
        h = hashlib.sha256()
        h.update(self.__to_hashable().encode("utf8"))
        return h.hexdigest()

    def pub_trans(self):
        obj = {
            "sender": self.sender_address,
            "recipient": self.recipient_address,
            "amount": self.amount,
        }
        return obj

    def __calculate_txt_hash(self):
        trans = {
            "sender": self.sender_address,
            "recipient": self.recipient_address,
            "amount": self.amount
        }
        sha256 = hashlib.sha256()
        data = json.dumps(trans)
        sha256.update(data.encode("utf8"))
        return sha256.hexdigest()
        
    def to_dict(self):
        dic = {}
        for k, v in self.__dict__.items():
            if k == "_Transaction__private_key":
                continue
            else:
                dic[k] = v
        return dic

    @classmethod
    def from_dict(cls, trans_dict):
        return cls(
            trans_dict["sender_address"],
            "",
            trans_dict["recipient_address"],
            trans_dict["amount"],
            trans_dict["signature"],
            trans_dict["txt_hash"],
            trans_dict["timestamp"]
        )

    def __sign(self, message):
        key = RSA.import_key(base64.b64decode(self.__private_key))
        signer = pkcs1_15.new(key)
        h = SHA256.new()
        h.update(f"{message}".encode("utf8"))
        signature = base64.b64encode(signer.sign(h)).decode("ascii")
        return signature

class Wallet(object):
    
    def __init__(self, wallet_name):
        self.wallet_name = wallet_name
        self.user = getpass.getuser()
        env = platform.system()
        if env == 'Linux':
            if not os.path.exists(f"/home/{self.user}/.mycoin"):
                os.mkdir(f"/home/{self.user}/.mycoin")
            self.filename = f"/home/{self.user}/.mycoin/{self.wallet_name}.json"
        elif env == 'Windows':
            if not os.path.exists(f"C:/Users/{self.user}/.mycoin"):
                os.mkdir(f"C:/Users/{self.user}/.mycoin")
            self.filename = f"C:/Users/{self.user}/{self.wallet_name}.json"

    @staticmethod
    def __generate_keys():
        gen_rand = Crypto.Random.new().read
        private_key = RSA.generate(4096, gen_rand)
        public_key = private_key.publickey()
        keys = {
            "public_key":  base64.b64encode(public_key.export_key(format="DER")).decode("ascii"),
            "private_key": base64.b64encode(private_key.export_key(format="DER")).decode("ascii")
        }
        return keys

    def create_wallet(self, password=None, verif_pass=None):
        keys = self.__generate_keys()
        public_key = keys["public_key"]
        private_key = keys["private_key"]
        msg = self.__encrypt_keys(public_key, private_key, password, verif_pass)
        return msg
    
    def __encrypt_keys(self, public_key, private_key, password=None, verif_pass=None):
        if password == None and verif_pass == None:
            password = getpass.getpass("Enter password: ")
            verif_pass = getpass.getpass("Verify password: ")
        if password != verif_pass:
            raise VerifyPasswordError()
        data = {
            "password" : encrypt(bcrypt_encrypt(password).decode(), password),
            "public_key": encrypt(public_key, password),
            "private_key": encrypt(private_key, password)
        }
        msg = self.__new_wallet(data)
        return msg
    
    def __new_wallet(self, data):
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if os.path.exists(self.filename):
            raise WalletError()
        umask = os.umask(0)
        try:
            fd = os.open(self.filename, flags, 0o400)
        finally:
            os.umask(umask)
        with os.fdopen(fd, "w") as fh:
                fh.write(json.dumps(data))
        return f"new wallet created, {self.wallet_name}"

    def new_transaction(self, recipient, amount, password=None):
        return self.__new_transaction(recipient, amount, password)

    def __new_transaction(self, recipent, amount, password=None):
        data = ""
        with open(self.filename, "r") as fh:
            data = json.load(fh)
        if data == "":
            raise LoadError()
        if password == None:
            password = getpass.getpass("Enter password: ")
        bhash = decrypt(data["password"], password).encode() 
        verified = bcrypt_validate(password, bhash)
        if not verified:
            raise VerifyPasswordError()
        priv_key = decrypt(data["private_key"], password)
        pub_key = decrypt(data["public_key"], password)
        trans = Transaction(pub_key, priv_key, recipent, amount)
        return trans