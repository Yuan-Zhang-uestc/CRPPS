from hash import sha256, get_binary_hash

class SparseMerkleTreeNode:
    def __init__(self, hash_value, parent = None, left = None, right = None, data = None):
        self.hash_value = hash_value
        self.parent = parent
        self.left = left
        self.right = right
        self.data = data

class SparseMerkleTree:
    def __init__(self, depth):
        self.depth = depth
        self.empty_hash = self.get_empty_hash()
        self.root = SparseMerkleTreeNode(self.empty_hash)
    
    def get_empty_hash(self):

        empty_hash = sha256('0')
        return empty_hash
    
    def update(self, data, leaf_hash, bitmap):
        self._update_tree(self.root, leaf_hash, bitmap, 0, data)
        proof = self.get_proof(self.root, bitmap)
        return proof
    
    def _update_tree(self, node, leaf_hash, bitmap, level, data):
        if level == self.depth:
            if node.hash_value != self.empty_hash:
                print("The location already has data stored. Please renegotiate.")
                return
            node.hash_value = leaf_hash
            node.data = data
            self._update_hash(node)
            return

        if bitmap[level] == '0':
            if node.left == None:
                node.left = SparseMerkleTreeNode(self.empty_hash, node)
            self._update_tree(node.left, leaf_hash, bitmap, level + 1, data)
        else:
            if node.right == None:
                node.right = SparseMerkleTreeNode(self.empty_hash, node)
            self._update_tree(node.right, leaf_hash, bitmap, level + 1, data)

    def _update_hash(self, node):
        current_node = node

        while current_node.parent is not None:
            parent_node = current_node.parent

            left_hash = parent_node.left.hash_value if parent_node.left else self.empty_hash
            right_hash = parent_node.right.hash_value if parent_node.right else self.empty_hash
            parent_node.hash_value = sha256(str(left_hash + right_hash))

            current_node = parent_node
    
    def get_proof(self, root, bitmap):
        proof = []
        current_node = root
        
        for level in range(self.depth):
            if bitmap[level] == '0':
                if current_node.right:
                    proof.append(current_node.right.hash_value)
                else:
                    proof.append(self.empty_hash)
                current_node = current_node.left
            else:
                if current_node.left:
                    proof.append(current_node.left.hash_value)
                else:
                    proof.append(self.empty_hash)
                current_node = current_node.right
        
        return proof

    def get_root(self):
        return self.root.hash_value
    
    def get_data(self, bitmap):
        current_node = self.root
        for level in range(self.depth):
            if bitmap[level] == '0':
                current_node = current_node.left
            else:
                current_node = current_node.right
        
        return current_node.data
 
if __name__ == "__main__":
    smt = SparseMerkleTree(256)

    hash = sha256("data1")
    proof = smt.update(["data1","test"], hash, get_binary_hash("key"))
    res = sha256("data1")
    for i in range(len(proof)):
        res = sha256(str(res+proof[i]))
    print(res)
    print(smt.get_root())
    print(smt.get_data(get_binary_hash("key")))

    