from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import bcrypt, bcrypt_check
from base64 import b64encode, b64decode

def bcrypt_encrypt(p):
    b64 = b64encode(SHA256.new(p.encode()).digest())
    bhash = bcrypt(b64, 16)
    return bhash

def bcrypt_validate(p, bhash):
    try:
        b64 = b64encode(SHA256.new(p.encode()).digest())
        bcrypt_check(b64, bhash)
    except ValueError:
        return False
    return True
    