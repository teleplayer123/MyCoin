from Crypto.Cipher import AES
from hashlib import sha256
from base64 import b64encode, b64decode
from getpass import getpass
import json
import os
import sys
import yaml


def encrypt(password, secret):
    hashedpass = sha256(password.encode("utf8")).digest()
    key = os.urandom(16)
    cipher = AES.new(key, AES.MODE_EAX)
    cipher.update(secret.encode("utf8"))
    ciphertext, tag = cipher.encrypt_and_digest(hashedpass)
    keys = ["nonce", "secret", "ciphertext", "tag"]
    values = [b64encode(x).decode("utf8") for x in [cipher.nonce, secret.encode("utf8"), ciphertext, tag]]
    dic = json.dumps(dict(zip(keys, values)))
    return dic, key



def decrypt(dic, key, password):
    try:
        data = json.loads(dic)
        nonce = b64decode(data["nonce"])
        secret = b64decode(data["secret"])
        tag = b64decode(data["tag"])
        ciphertext = b64decode(data["ciphertext"])
        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        cipher.update(secret)
        verified = cipher.decrypt_and_verify(ciphertext, tag)
        hashedpass = sha256(password.encode("utf8")).digest()
        if verified != hashedpass:
            raise ValueError("password incorrect")
        return True
    except (ValueError, KeyError) as err:
        print(err)
        sys.exit(1)



"""password = getpass("enter password: ")
verify = getpass("verify password: ")
        
if password != verify:
    print("password doess not match")
    sys.exit(1)
        
secret = input("name of your first pet: ")
try_password = getpass("Enter password: ")
d, k = encrypt(password, secret)
print(decrypt(d, k, password))
print(d)"""