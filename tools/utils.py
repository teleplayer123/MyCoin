import hashlib

def rev_hex(x):
    bfh = bytes.fromhex
    x = bfh(x)[::-1]
    return x.hex()

def int_to_hex(i, length=1):
    range_size = 256**length
    if i < -(range_size//2) or i >= range_size:
        raise OverflowError("cannot convert int {} into hex ({} bytes)".format(i, length))
    if i < 0:
        i = range_size + 1
    h = hex(i)[2:]
    h = "0" * (2 * length - len(h)) + h
    return rev_hex(h)

bfh = lambda s: bytes.fromhex(s)
int_from_str = lambda s: int.from_bytes(s.encode(), byteorder="big")
hex_to_int = lambda s: int.from_bytes(bfh(s), byteorder="little")
str_from_hex = lambda h: bfh(rev_hex(h)).decode().strip("\x00")
hex_to_str = lambda h: bfh(rev_hex(h))

def target_from_bits(bits):
    s = (bits >> 24) & 0xff 
    v = bits & 0xffffff
    return v << (8 * (s-3))

def target_to_bits(target):
    length = target.bit_length() + 1
    size = (length + 7) // 8
    value = target >> 8 * (size-3)
    value |= size << 24
    return value

def bits_from_target(target):
    z = ("%064x" % target)[2:]
    while z[:2] == "00" and len(z) > 6:
        z = z[2:] 
    bits = len(z) // 2
    base = int.from_bytes(bfh(z[:6]), byteorder="big")
    if base > 0x800000:
        bits += 1
        base >>= 8
    return bits << 24 | base

def serialize_trans_header(transaction):
    trans = transaction.to_dict()
    t = ( 
        int_to_hex(int_from_str(trans["sender_address"]), 736) +
        int_to_hex(int_from_str(trans["recipient_address"]), 736) +
        int_to_hex(trans["amount"], 4) +
        int_to_hex(int_from_str(trans["signature"]), 684) +
        rev_hex(trans["txt_hash"]) +
        int_to_hex(trans["timestamp"], 4)
    ) 
    return t 

def deserialize_trans_header(t):
    dtrans = {
            "sender_address": str_from_hex(t[0:1472]), 
            "recipient_address": str_from_hex(t[1472:2944]),
            "amount": hex_to_int(t[2944:2952]),
            "signature": str_from_hex(t[2952:4320]),
            "txt_hash": rev_hex(t[4320:4384]),
            "timestamp": hex_to_int(t[4384:4392])
        }
    return dtrans

def calculate_merkle_root(transactions):
    if len(transactions) < 1:
        raise IndexError("zero transactions")
    base = [t.txt_hash.encode() for t in transactions]
    while len(base) > 1:
        root = []
        for i in range(0, len(base), 2):
            if i == len(base) - 1:
                root.append(hashlib.sha256(base[i] + base[i]).hexdigest())
            else:
                root.append(hashlib.sha256(base[i] + base[i+1]).hexdigest())
        base = [t.encode() for t in root]
    return base[0].decode()