from bplib.bp import BpGroup

class KeyManager:
    def __init__(self):

        self.group = BpGroup()

    def generate_keys(self):
        """
        Generate and return a public/private key pair.
        """
        private_key = self.group.order().random()
        g2=self.group.g2
        public_key = g2.mul(private_key)
        return private_key, public_key
