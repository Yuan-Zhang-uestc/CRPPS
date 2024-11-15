import sys
import time
from hashlib import blake2b
from typing import List, Tuple
from math import log2

from petlib.bn import Bn #big number class
from petlib.ec import EcGroup, EcPt
#pairing
from bplib.bp import BpGroup, G1Elem, G2Elem
from key import KeyManager


CUCKOO_FILTER_CAPACITY_MIN = 1000
CUCKOO_FILTER_CAPACITY_FRACTION = 0.3
CUCKOO_FILTER_BUCKET_SIZE = 6
CUCKOO_FILTER_FINGERPRINT_SIZE = 4
DOC_ID_SIZE = 4
EC_NID_DEFAULT = 415
ENCODING_DEFAULT = "utf-8"


def kwd_encode(doc_id:bytes, kwd:bytes) -> bytes:
    return blake2b(doc_id + kwd).digest()


class Purchaser:

    def __init__(self, number_docs_published,group: BpGroup,g1:G1Elem,g2:G2Elem):

        self.group = group
        self.g1 = g1
        self.g2 = g2

        key_manager = KeyManager()
        self.private_key, self.public_key = key_manager.generate_keys()
        self.number_docs_published=number_docs_published
        self.inf=G1Elem.inf(self.group)
        self.ord=self.group.order()

    def require_issue(self, kwds:List[str]) -> Tuple[Bn, List[bytes], G1Elem,G2Elem]:

        #secret c
        secret = self.group.order().random()

        query_enc = list()

        for kwd in kwds:
            kwd_pt = self.group.hashG1(kwd.encode(ENCODING_DEFAULT))
            kwd_enc = kwd_pt.mul(secret)
            kwd_enc_bytes = kwd_enc.export()
            query_enc.append(kwd_enc_bytes)

        #sigma_b
        query_enc_bytes = b''.join(query_enc)
        query_hash =self.group.hashG1(query_enc_bytes+self.public_key.export())
        sigma_b=query_hash.mul(self.private_key)

        return (secret, query_enc,sigma_b,self.public_key)


    def attr_comfirm(self, secret:Bn, reply:List[Bn], published:List[Tuple[int, bytes]], powers: List[List[G1Elem]]) -> List[int]:
    # def attr_comfirm(self, secret: Bn, reply: List[Bn], published: List[Tuple[int, bytes]]) -> List[int]:

        secret_inv = secret.mod_inverse(self.ord)#C
        secret_inv_bit=bin(secret_inv)[2:]#二进制bit

        # count_ones = secret_inv_bit.count('1')
        #
        # if count_ones > self.ord/2:
        #     print("The number of '1's is greater than half of the group order!")
        #     sys.exit()

        cardinalities = []

        # For optimisation the following assumptions are made
        # - all keywords in the query are different.
        # - all keywords in the document are different.
        kwds_dec = list()
        count=0
        # powers=[]
        for kwd_h in reply:
            # kwd_pt = G1Elem.from_bytes(kwd_h, self.group)
            T = self.inf

            # power_row = []
            # power_value = kwd_pt
            #
            # power_row.append(power_value)
            # j = Bn.from_decimal("2")
            # while j <= self.ord:
            #     power_value = power_value.double()
            #     power_row.append(power_value)
            #     j *= 2
            #
            # powers.append(power_row)

            for j in range(len(secret_inv_bit)):
                if secret_inv_bit[len(secret_inv_bit)-j-1]:
                    T.add(powers[count][j])


            kwd_pt_dec=T
            kwd_bytes = kwd_pt_dec.export()
            kwds_dec.append(kwd_bytes)

            count += 1

        # n_docs = max(doc_id for doc_id, _ in published) + 1
        # for doc_id in range(n_docs):
        #     n_matches = 0
        #     encoded_doc_id = doc_id.to_bytes(DOC_ID_SIZE, byteorder="big")
        #     for kwd_dec in kwds_dec:
        #         kwd_docid_bytes = kwd_encode(encoded_doc_id, kwd_dec)
        #         if any(kwd_docid_bytes == pub_kwd for pub_doc_id, pub_kwd in published if pub_doc_id == doc_id):
        #             n_matches += 1
        #     cardinalities.append(n_matches)

        return cardinalities


class Seller:


    def __init__(self, number_docs_published,group: BpGroup,g1:G1Elem,g2:G2Elem):

        self.group = group
        self.g1 = g1
        self.g2 = g2

        key_manager = KeyManager()
        self.private_key, self.public_key = key_manager.generate_keys()
        self.number_docs_published = number_docs_published
        self.ord=self.group.order()


    def attr_issue(self, docs:List[List[str]]) -> Tuple[Bn, List[Tuple[int, bytes]], Bn]:

        #generate secret s
        secret = self.group.order().random()

        tag_collection=[]

        for doc_id, kwds in enumerate(docs):
            encoded_doc_id = doc_id.to_bytes(DOC_ID_SIZE, byteorder="big")
            for kwd in kwds:
                kwd_byte=kwd.encode(ENCODING_DEFAULT)
                kwd_pt = self.group.hashG1(kwd_byte)
                kwd_enc = kwd_pt.mul(secret)
                kwd_enc_bytes = kwd_enc.export()
                kwd_docid_bytes = kwd_encode(encoded_doc_id, kwd_enc_bytes)

                tag_collection.append((doc_id, kwd_docid_bytes))

        #record
        rec = self.public_key.export() + b''.join(
            doc_id.to_bytes(DOC_ID_SIZE, byteorder="big") + kwd_docid_bytes
            for doc_id, kwd_docid_bytes in tag_collection
        ) + self.number_docs_published.to_bytes(4, byteorder="big")

        #sigma_rec
        rec_g1 = self.group.hashG1(rec)
        sigma_rec = rec_g1.mul(self.private_key)

        return (secret, tag_collection, sigma_rec)


    # def require_response(self, secret:Bn, query:List[bytes], sigma_b: G1Elem, purchaser_pk:G2Elem) -> List[Bn]:#Tuple[List[Bn], List[List[G1Elem]]]:
    def require_response(self, secret: Bn, query: List[bytes], sigma_b: G1Elem, purchaser_pk: G2Elem) -> Tuple[List[Bn], List[List[G1Elem]]]:

        
        #pairing
        e1=self.group.pair(sigma_b,self.g2)

        query_bytes = b''.join(query)
        combined_input = query_bytes + self.public_key.export()
        combined_input_g1 = self.group.hashG1(combined_input)
        e2=self.group.pair(combined_input_g1,purchaser_pk)

        # if e1 == e2:
        #     print("require_response continues!")
        # else:
        #     print("require_response aborts!")


        reply = list()
        max_power = self.ord
        powers=[]
        for kwd_h in query:
            kwd_g1 = G1Elem.from_bytes(kwd_h, self.group)
            kwd_enc = kwd_g1.mul(secret)
            kwd_enc_bytes = kwd_enc.export()
            reply.append(kwd_enc_bytes)

            power_row = []
            power_value=kwd_enc

            power_row.append(power_value)
            j=Bn.from_decimal("2")
            while j <= max_power:
                power_value = power_value.double()
                power_row.append(power_value)
                j *=2

            powers.append(power_row)

        # return reply
        return reply,powers