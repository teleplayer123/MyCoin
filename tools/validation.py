from storage.peers import Peers
from storage.blacklist import BlackList

def allow_peer(peer):
    peers = Peers()
    valid_peers = [p for p in peers.get_all_peers()]
    if peer in valid_peers:
        return True
    return False

def blocked_host(host):
    blacklist = BlackList()
    denied_hosts = blacklist.get_blacklisted()
    if host in denied_hosts:
        return True
    return False