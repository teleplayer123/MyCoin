from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
import base64
import json
import os
import struct
from time import time
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from block import Block, BlockHeader
from wallet import Transaction
from tools.utils import int_to_hex, bfh, hex_to_int, rev_hex, int_from_str, str_from_hex
from config import config 

GENESIS_BITS = config["network"]["genesis_bits"]
VERSION = config["network"]["version"]
MAX_TRANS = config["network"]["max_transactions"]

class TRANS_SIZE_ERROR(Exception):
    def __str__(self):
        return "Transactions size incorrect"


class BlockchainStorage(object):

    def __init__(self):
        self.__block = Block
        self.__block_header = BlockHeader
        self.__filename = config["user"]["serialized_blocks"]
        self.__trans_filename = config["user"]["trans_fname"]
        self.__block_struct = struct.Struct("<176s")
        self.__trans_struct = struct.Struct("<64s{}s".format(4392*MAX_TRANS))
        if not os.path.exists(self.__filename):
            self.__mode = "wb+"
            self.genesis_block()
        else:
            self.__mode = "rb+"
        
    def genesis_block(self):
        block = Block(
            0,
            "0"*64,
            hex(GENESIS_BITS)[2:],
            1,
            [],
            "0"*64,
            int(time()),
            1,
            VERSION)
        self.add_block(block)

    def serialize_trans_header(self, transactions):
        strans = []
        for transaction in transactions:
            if not isinstance(transaction, Transaction):
                logger.debug("Invalid type, must be instance of Transaction")
                raise TypeError("type must be instance of class Transaction")
            trans = transaction.to_dict()
            t = ( 
                int_to_hex(int_from_str(trans["sender_address"]), 736) +
                int_to_hex(int_from_str(trans["recipient_address"]), 736) +
                int_to_hex(trans["amount"], 4) +
                int_to_hex(int_from_str(trans["signature"]), 684) +
                rev_hex(trans["txt_hash"]) +
                int_to_hex(trans["timestamp"], 4)
            ) 
            strans.append(t)
        return "".join(strans)

    def deserialize_trans_header(self, strans_block):
        sblock_size = 4392
        if len(strans_block) % sblock_size != 0:
            logger.error("block length is of unacceptable size.")
            raise TRANS_SIZE_ERROR()
        trans = []
        num_trans = int(len(strans_block) / 4392)
        i = 0
        while True:
            t = strans_block[i:sblock_size]
            dtrans = {
                "sender_address": str_from_hex(t[0:1472]), 
                "recipient_address": str_from_hex(t[1472:2944]),
                "amount": hex_to_int(t[2944:2952]),
                "signature": str_from_hex(t[2952:4320]),
                "txt_hash": rev_hex(t[4320:4384]),
                "timestamp": hex_to_int(t[4384:4392])
            }
            trans.append(dtrans)
            if len(trans) == num_trans:
                break
            i = sblock_size
            sblock_size += 4392
        return trans     


    def serialize_block_header(self, header_dict):
        block = (
            int_to_hex(header_dict["index"], 4) +
            rev_hex(header_dict["previous_hash"]) + 
            rev_hex(header_dict["bits"]) +
            int_to_hex(header_dict["difficulty"], 4) +
            rev_hex(header_dict["merkle_root"]) +
            int_to_hex(header_dict["timestamp"], 4) +
            int_to_hex(header_dict["proof"], 4) + 
            int_to_hex(header_dict["version"], 4)
        )
        return block

    def deserialize_block_header(self, sheader):
        index = hex_to_int(sheader[:8])
        prev_hash = rev_hex(sheader[8:72])
        bits = rev_hex(sheader[72:80])
        difficulty = hex_to_int(sheader[80:88])
        merkle_root = rev_hex(sheader[88:152])
        timestamp = hex_to_int(sheader[152:160])
        proof = hex_to_int(sheader[160:168])
        version = hex_to_int(sheader[168:176])
        return {
            "index": index,
            "previous_hash": prev_hash,
            "bits": bits,
            "difficulty": difficulty,
            "merkle_root": merkle_root,
            "timestamp": timestamp,
            "proof": proof,
            "version": version
        }

    def add_block(self, block):
        if isinstance(block, Block):
            index = block.block_header.index
            block_header = block.to_dict()["block_header"]
            transactions = block.transactions
        else:
            logger.debug("invalid block: %s must be instance of Block", type(block))
            raise TypeError("Invalid block type")
        strans = self.serialize_trans_header(transactions)
        if len(transactions) > 0:
            self.write_transactions(strans, block_header["merkle_root"])
        sblock = self.serialize_block_header(block_header)
        offset = index * self.__block_struct.size
        packed_block = self.__block_struct.pack(sblock.encode())
        status = False
        try:
            with open(self.__filename, self.__mode) as fh:
                fh.seek(offset)
                fh.write(packed_block)
            status = True
        except os.error as err:
            logger.error(err)
            status = False
        logger.info("new block {} at index {}".format(block_header["merkle_root"], block_header["index"]))
        return status


    def write_transactions(self, serialized_trans, merkle_root, filename=None):
        branch = False
        packed_trans = self.__trans_struct.pack(merkle_root.encode(), serialized_trans.encode())
        offset = hex_to_int(merkle_root) % 37 * self.__trans_struct.size
        if filename == None:
            filename = self.__trans_filename.format("root_0")
        if not os.path.exists("data/txs"):
            os.mkdir("data/txs")
        if not os.path.exists(filename):
            umask = os.umask(0)
            try:
                fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            finally:
                os.umask(umask)
            with os.fdopen(fd, "wb+") as fh:
                fh.seek(offset)
                fh.write(packed_trans)
        else:
            prev_fn = None
            try:
                for _, _, filenames in os.walk("data/txs", followlinks=True):
                    if len(filenames) < 2:
                        break
                    else:
                        for fn in filenames:
                            if fn == "root_0.bin":
                                prev_fn = fn
                                continue
                            m = fn.split("_")[1][:-4]
                            if hex_to_int(m) > hex_to_int(merkle_root):
                                filename = self.__trans_filename.format(prev_fn)
                                break
                            else:
                                prev_fn = fn
                if prev_fn is not None:
                    filename = prev_fn
            except os.error as err:
                logger.error(" Error writing txs: {}".format(err))

            with open(filename, "rb+") as fh:
                fh.seek(offset)
                t = fh.read(self.__trans_struct.size)
                logger.debug(" read trans: {}".format(t.decode()))
                if len(t.decode()) == 0:
                    fh.write(packed_trans)
                else:
                    branch = True
            if branch == True:
                fbranch = self.__trans_filename.format("root_{}".format(merkle_root))
                logger.info(" Forking txs file: {}".format(fbranch))
                self.write_transactions(serialized_trans, merkle_root, filename=fbranch)
        return branch


    def get_trans_from_last_block(self):
        lb = self.get_last_block()
        merkle = lb.merkle_root
        offset = hex_to_int(merkle) % 37 * self.__trans_struct.size
        with open(self.__trans_filename.format("root_0"), "rb+") as fh:
            fh.seek(offset)
            pdata = fh.read(self.__trans_struct.size)
            data = self.__trans_struct.unpack(pdata)
        trans = self.deserialize_trans_header(data[1].decode())
        return trans
        

    def get_trans_by_merkle(self, merkle_root):
        offset = hex_to_int(merkle_root) % 37 * self.__trans_struct.size
        with open(self.__trans_filename.format("root_0"), "rb+") as fh:
            fh.seek(offset)
            pdata = fh.read(self.__trans_struct.size)
            data = self.__trans_struct.unpack(pdata)
        trans = self.deserialize_trans_header(data[1].decode())
        return trans


    def get_block_by_index(self, index):
        with open(self.__filename, self.__mode) as fh:
            fh.seek(0, os.SEEK_END)
            end = fh.tell()
            offset = index * self.__block_struct.size
            if offset > end:
                raise IndexError("error retrieving block")
            fh.seek(offset)
            block = self.__block_struct.unpack(fh.read(self.__block_struct.size))[0]
            block = self.deserialize_block_header(block.decode())
            return self.__block_header.from_dict(block)


    def get_last_block(self):
        with open(self.__filename, self.__mode) as fh:
            fh.seek(0, os.SEEK_END)
            end = fh.tell()
            offset = end - self.__block_struct.size
            fh.seek(offset)
            block =  self.__block_struct.unpack(fh.read(self.__block_struct.size))[0]
            block = self.deserialize_block_header(block.decode())
            return self.__block_header.from_dict(block)