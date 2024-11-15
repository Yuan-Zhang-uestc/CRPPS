import os
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.kdf.concatkdf import ConcatKDFHash
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import bplib.bp as bp
from hash import sha256, get_binary_hash
import smt

def generate_parameters():
    group = bp.BpGroup()

    g1 = group.gen1()
    g2 = group.gen2()
    return group, g1, g2

def generate_key_pair(group, g2):
    private_key = group.order().random()
    public_key = private_key * g2
    return private_key, public_key

def generate_shared_key(private_key, peer_public_key):
    shared_key = private_key * peer_public_key
    return shared_key

def hkdf(key_material, length=32, salt=None, info=b'ratchet'):
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
        backend=default_backend()
    )
    return hkdf.derive(key_material)

def encrypt_message(key, message, associated_data=b''):
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # GCM 需要 96 位 (12 字节) 的随机 nonce
    ciphertext = aesgcm.encrypt(nonce, message.encode(), associated_data)
    return nonce, ciphertext

def decrypt_message(key, nonce, ciphertext, associated_data=b''):
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
    return plaintext.decode()


class DoubleRatchet:
    def __init__(self, shared_key, group, g1, g2):

        self.group = group
        self.g1 = g1
        self.g2 = g2
        self.shared_key = shared_key.export()
        self.send_chain_key = shared_key.export()
        self.recv_chain_key = shared_key.export()
        self.dh_key_pair = generate_key_pair(group, g2)
        self.dh_private_key = self.dh_key_pair[0]
        self.dh_public_key = self.dh_key_pair[1]
    
    def ratcher_send_key(self, peer_public_key):

        salt = generate_shared_key(self.dh_private_key, peer_public_key)
        self.send_chain_key = hkdf(self.send_chain_key, salt=salt.export())
        current_dh_public_key = self.dh_public_key
        self.dh_key_pair = generate_key_pair(self.group, self.g2)
        self.dh_private_key = self.dh_key_pair[0]
        self.dh_public_key = self.dh_key_pair[1]
        return self.send_chain_key, current_dh_public_key
    
    def ratchet_send(self, message):
        message_key = self.send_chain_key
        nonce, ciphertext = encrypt_message(message_key, message)
        return nonce, ciphertext

    def ratcher_recv_key(self, peer_public_key):

        salt = generate_shared_key(self.dh_private_key, peer_public_key)
        self.recv_chain_key = hkdf(self.recv_chain_key, salt=salt.export())
        return self.recv_chain_key
    
    def ratchet_recv(self, nonce, ciphertext):
        message_key = self.recv_chain_key
        plaintext = decrypt_message(message_key, nonce, ciphertext)
        return plaintext


if __name__ == "__main__":
    group, g1, g2 = generate_parameters()

    seller_private_key, seller_public_key = generate_key_pair(group, g2)
    buyer_private_key, buyer_public_key = generate_key_pair(group, g2)

    seller_shared_key = generate_shared_key(seller_private_key, buyer_public_key)
    buyer_shared_key = generate_shared_key(buyer_private_key, seller_public_key)

    seller_ratchet = DoubleRatchet(seller_shared_key, group, g1, g2)
    buyer_ratchet = DoubleRatchet(buyer_shared_key, group, g1, g2)

    message = "Hello!"
    seller_message_key, seller_dh_pub = seller_ratchet.ratcher_send_key(buyer_ratchet.dh_public_key)
    nonce, ciphertext = seller_ratchet.ratchet_send(message)

    data = [nonce, ciphertext]

    buyer_message_key = buyer_ratchet.ratcher_recv_key(seller_dh_pub)

    seller_addr = "addr" + seller_message_key.hex()
    seller_bitmap = get_binary_hash(seller_addr)

    tree = smt.SparseMerkleTree(256)

    hash = sha256(data[1].hex())
    proof = tree.update(data, hash, seller_bitmap) 

    buyer_addr = "addr" + buyer_message_key.hex()
    buyer_bitmap = get_binary_hash(buyer_addr)

    data = tree.get_data(buyer_bitmap)
    res = sha256(data[1].hex())
    for i in range(len(proof)):
        res = sha256(str(res+proof[i]))
    if res == tree.get_root():
        plaintext = buyer_ratchet.ratchet_recv(data[0], data[1])
        print(plaintext)


