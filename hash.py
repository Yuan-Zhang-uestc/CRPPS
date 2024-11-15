import hashlib


def sha256(data):
    hex_hash = hashlib.sha256(data.encode('utf-8')).hexdigest()
    int_hash = int(hex_hash, 16)
    return int_hash

def get_binary_hash(data):
    hex_hash = hashlib.sha256(data.encode('utf-8')).hexdigest()

    binary_hash = bin(int(hex_hash, 16))[2:]

    binary_hash = binary_hash.zfill(256)

    return binary_hash

if __name__ == "__main__":   
    data1 = "test1"
    test1 = sha256(data1)
    print(test1)

    data2 = "test2"
    test2 = sha256(data2)
    print(test2)
    
    test3 = sha256(str(test1 + test2))
    print(test3)
    binary_representation = get_binary_hash(data1)
    
    print("SHA-256 Hash in binary (bit representation):")
    print(binary_representation)
    print(f"Length of binary representation: {len(binary_representation)} bits")