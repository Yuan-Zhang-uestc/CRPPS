#!/usr/bin/env python3

import sys
import random
import time
import datetime
import string
import json
from bplib.bp import BpGroup, G1Elem, G2Elem
from key import KeyManager

sys.path.append('./')
sys.path.append('..')
from match import Purchaser,Seller

KEYWORD_LENGTH = 16
DEFAULT_CURVE = 415

DOCUMENT_NUMBER = [ int(10**(i / 3)) for i in range(3, 13)]
DOCUMENT_ATTRIBUTE_NUMBER = (10000,)
QUERY_ATTRIBUTE_NUMBER = (10000,)


class BenchmarkMatch:
    def __init__(self, data, number_docs_published, number_kwds_per_doc, number_kwds_per_query, repetitions=1, repetitions_publish=1):
        random.seed(0)

        self.data = data

        self.repetitions = repetitions
        self.repetitions_publish = repetitions_publish
        self.number_docs_published = number_docs_published
        self.number_kwds_per_doc = number_kwds_per_doc
        self.number_kwds_per_query = number_kwds_per_query

        self.kwds_published = [[(''.join((random.choice(string.ascii_lowercase) for _ in range(KEYWORD_LENGTH)))) for _ in range(number_kwds_per_doc)] for _ in range(number_docs_published)]
        self.kwds_query = [[(''.join((random.choice(string.ascii_lowercase) for _ in range(KEYWORD_LENGTH)))) for _ in range(number_kwds_per_query)] for _ in range(repetitions)]

        self.group = BpGroup()
        self.g1 = self.group.gen1()
        self.g2 = self.group.gen2()

        self.match_purchaser = Purchaser(self.number_docs_published,self.group,self.g1,self.g2)
        self.match_seller = Seller(self.number_docs_published,self.group,self.g1,self.g2)



    def run(self):
        t0 = time.process_time()
        (secret_seller, issued,sigma_rec) = self.match_seller.attr_issue(self.kwds_published)
        t1 = time.process_time()
        attr_issue_time = t1 - t0
        print(f"{attr_issue_time}")

        times = []
        lengths = []
        queries = []
        for kwds in self.kwds_query:
            t0 = time.process_time()
            query = self.match_purchaser.require_issue(kwds)
            t1 = time.process_time()
            require_issue_time = t1 - t0
            print(f"{require_issue_time}")

            times.append(t1-t0)

            length = sum(map(lambda x: len(x), query[1]))
            lengths.append(length)

            queries.append(query)

        self.data['query'][self.number_docs_published][self.number_kwds_per_doc][self.number_kwds_per_query] = {'time': times, 'length': lengths}

        times = []
        lengths = []
        replies = []
        for query in queries:
            t0 = time.process_time()
            (reply,powers) = self.match_seller.require_response(secret_seller, query[1], query[2],query[3])
            # (reply) = self.match_seller.require_response(secret_seller, query[1], query[2], query[3])
            t1 = time.process_time()
            require_response_time = t1 - t0
            print(f"{require_response_time}")

            length = sum(map(lambda x: len(x), reply))
            length += sum(len(elem.export()) for row in powers for elem in row)

            times.append(t1-t0)
            lengths.append(length)

            replies.append(reply)

        self.data['reply'][self.number_docs_published][self.number_kwds_per_doc][self.number_kwds_per_query] = {'time': times, 'length': lengths}

        times = []
        for i, reply in enumerate(replies):
            t0 = time.process_time()
            self.match_purchaser.attr_comfirm(queries[i][0], reply, issued, powers)
            # self.match_purchaser.attr_comfirm(queries[i][0], reply, issued)
            t1 = time.process_time()
            attr_comfirm_time = t1 - t0

            print(f"{attr_comfirm_time} ")
            print()

            times.append(t1-t0)

        self.data['cardinality'][self.number_docs_published][self.number_kwds_per_doc][self.number_kwds_per_query] = {'time': times, 'length':[]}


def write_data(filename, data):
    structure = {}
    for op in data.keys():
        elem = []
        for d in data[op].keys():
            for p in data[op][d].keys():
                for q in data[op][d][p].keys():
                    times = {
                        'n_document_published': d,
                        'n_kwd_per_doc': p,
                        'n_kwd_per_query': q,
                        'times' : data[op][d][p][q]['time'],
                        'lengths' : data[op][d][p][q]['length']
                    }
                    elem.append(times)
        structure[op] = elem

    content = json.dumps(structure)


    with open(filename, 'w') as fd:
        fd.write(content)


if __name__ == '__main__':
    data = {'publish': {}, 'query': {}, 'reply': {}, 'cardinality': {}}

    for n_docs_published in DOCUMENT_NUMBER:
        for op in data.keys():
            data[op][n_docs_published] = {}
            for n_kwds_per_doc in DOCUMENT_ATTRIBUTE_NUMBER:
                data[op][n_docs_published][n_kwds_per_doc] = {}

    for n_docs_published in DOCUMENT_NUMBER:
        for n_kwds_per_doc in DOCUMENT_ATTRIBUTE_NUMBER:
            print("Benchmarking #docs = {}, #kwds_per_doc = {}".format(n_docs_published, n_kwds_per_doc))
            for n_kwds_per_query in QUERY_ATTRIBUTE_NUMBER:
                BenchmarkMatch(data, n_docs_published, n_kwds_per_doc, n_kwds_per_query).run()

    date = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%s')
    write_data('benchmark-match-{}.json'.format(date), data)
