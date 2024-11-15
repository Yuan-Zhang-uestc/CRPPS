import time
import random
import string
from smt import SparseMerkleTree,SparseMerkleTreeNode
import os
from hash import sha256, get_binary_hash

def generate_random_string(size):

    return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

if __name__ == "__main__":

    smt = SparseMerkleTree(3)

    sizes = [4 * 1024,256 * 1024, 4 * 1024 * 1024]  # 4KB,256KB, 4MB
    size_labels = ["4KB", "256KB","4MB"]

    for size, label in zip(sizes, size_labels):

        data = generate_random_string(size)

        bitmap = get_binary_hash(data)

        start_time = time.time()
        hash_value = sha256(data)
        proof = smt.update(data, hash_value, bitmap)
        end_time = time.time()

        print(f"send execution time for {label} data: {end_time - start_time} seconds")

        start_time = time.time()
        proof1=smt.get_proof(smt.root, bitmap)
        retrieved_data = smt.get_data(bitmap)
        end_time = time.time()

        print(f"receive execution time for {label} data: {end_time - start_time} seconds")

        root=smt.get_root()
        res = hash_value
        start_time = time.time()
        for i in range(len(proof)):
            res = sha256(str(res + proof[-i-1]))
        end_time = time.time()

        print(f"verification execution time for {label} data: {end_time - start_time} seconds")
        print(res==root)