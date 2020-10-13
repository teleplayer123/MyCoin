import multiprocessing as mp
import logging

from blockchain import BlockChain
from storage.binbc import BlockchainStorage
from storage.mempool import Mempool
from tools.encrypt_decrypt import decrypt
from wallet import Transaction
from config import config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Miner(object):

    mining_process = None
    reward_pub = config["network"]["reward_public"]
    reward_priv = config["network"]["reward_private"]
    reward_recip = config["network"]["reward_recipient"]

    def __init__(self):
        mp.log_to_stderr()
        mp_logger = mp.get_logger()
        mp_logger.setLevel(logging.DEBUG)
        self.blockchain = BlockChain()
        self.block_pool = BlockchainStorage()
        self.memp = Mempool()

    def start(self):
        logger.debug("mining started")
        self.mining_process = mp.Process(target=self.mine)
        self.mining_process.start()
    

    def mine(self):
        while True:
            status, block = self.mine_block()
            if not block:
                logger.info("mining shutting down")
                print("miner stopping")
                break
            if status == True:
                logger.info("block {} found at index {} with proof {}".format(block.to_dict(), 
                                                    block.index, block.block_header.proof))
                self.memp.remove_unconfirmed_transactions()   
        if self.mining_process.is_alive():
            self.mining_process.close()

            
    def mine_block(self):
        transactions = [t for t in self.memp.get_all_unconfirmed_transactions()]
        if len(transactions) < 1:
            return False, None
        block = self.block_pool.get_last_block()
        last_proof = block.proof
        index = block.index + 1
        proof = self.blockchain.proof_of_work(last_proof)
        prev_hash = self.blockchain.hash(block.to_hashable())
        reward = Transaction(self.reward_pub, self.reward_priv, self.reward_recip, 1)
        if self.blockchain.verify_transaction(reward.sender_address, reward.recipient_address, 
                                         reward.signature, reward.amount):
            transactions.append(reward)
        new_block = self.blockchain.new_block(index, prev_hash, transactions, proof)
        return new_block  