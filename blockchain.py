import base64
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
import hashlib

from block import Block, BlockHeader
from storage.binbc import BlockchainStorage
from storage.mempool import Mempool
from config import config
from tools.utils import target_from_bits, bits_from_target, int_to_hex, hex_to_int

class BlockChain(object):

    def __init__(self):
        self._blockchain = BlockchainStorage()

    def new_block(self, index, previous_hash, transactions, proof):
        bits = self._blockchain.get_last_block().bits
        difficulty = 1
        if index % 10 == 0:
            target = self.calculate_target(int((index / 10)) - 1, bits)
            bits = bits_from_target(target)
            difficulty = self.difficulty_from_bits(bits)
        block = Block(
            index,
            previous_hash,
            bits,
            difficulty,
            transactions,
            proof=proof
        )

        status = self._blockchain.add_block(block)
        return status, block

    def calculate_target(self, index, bits):
        first = self._blockchain.get_block_by_index(index * 10)
        last = self._blockchain.get_block_by_index(index * 10 + 9)
        time_span = last.timestamp - first.timestamp
        target_time_span = config["network"]["target_timespan"]
        max_target = config["network"]["max_target"]
        target = target_from_bits(bits)
        time_span = max(time_span, target_time_span // 4)
        time_span = min(time_span, target_time_span * 4)
        new_target = max(max_target, (target * time_span) // target_time_span)
        new_target = target_from_bits(bits_from_target(new_target))
        return new_target

    def difficulty_from_bits(self, bits):
        difficulty_1_target = 0x00ffff * 2 ** (8 * (0x1d-3))
        target = target_from_bits(bits)
        difficulty = difficulty_1_target / float(target)
        return difficulty

    def verify_transaction(self, sender, recipient, signature, amount):
        msg = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount
        }
        if self.verify_signature(sender, msg, signature):
            return True
        else:
            return False

    @property
    def last_block(self):
        return self._blockchain.get_last_block()

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof 

    def valid_proof(self, last_proof, proof):
        difficulty = self._blockchain.get_last_block().difficulty
        guess = hashlib.sha256()
        guess.update(f"{last_proof}".encode("utf8") + f"{proof}".encode("utf8"))
        hashed_guess = guess.hexdigest()
        return hashed_guess[:difficulty] == "0" * difficulty
    
    @staticmethod
    def hash(block):
        sha256 = hashlib.sha256()
        block_str = block.encode("utf8")
        sha256.update(block_str)
        return sha256.hexdigest()


    def verify_signature(self, sender, message, signature):
        key = RSA.import_key(base64.b64decode(sender))
        cipher = pkcs1_15.new(key)
        h = SHA256.new()
        h.update(f"{message}".encode("utf8"))
        try:
            cipher.verify(h, base64.b64decode(signature))
            print("verified")
            return True
        except (ValueError, TypeError) as err:
            print(err)
            return False