import os
import json
from opensearchpy import OpenSearch

class ProposalESQuery:
    def __init__(self, block_time, call_functions, host='192.168.3.146', port=9200):
        auth = (os.getenv('OPENSEARCH_USER'), os.getenv('OPENSEARCH_PASSWORD'))
        self.index_name = 'eth_block'
        self.block_time = block_time
        self.call_functions = call_functions
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_compress=True,
            http_auth=auth,
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False
        )
        self.dsl_query = self.build_query()

    def build_query(self):
        return {
            "_source": False,
            "size": 20000,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "range": {
                                "Timestamp": {
                                    "gte": f"{self.block_time}-01-01",
                                    "lte": f"{self.block_time}-12-31"
                                }
                            }
                        },
                        {
                            "nested": {
                                "path": "Transactions",
                                "inner_hits": {
                                    "_source": [
                                        "Transactions.Hash",
                                        "Transactions.CallFunction",
                                        "Transactions.CallParameter",
                                        "Transactions.ConAddress",
                                        "Transactions.FromAddress",
                                        "Transactions.ToAddress",
                                        "Transactions.InternalTxns.CallFunction",
                                        "Transactions.InternalTxns.CallParameter",
                                        "Transactions.InternalTxns.ConAddress",
                                        "Transactions.InternalTxns.FromAddress",
                                        "Transactions.InternalTxns.ToAddress",
                                        "Transactions.InternalTxns.Type"
                                    ],
                                    "size": 100
                                },
                                "query": {
                                    "bool": {
                                        "should": [
                                            {"terms": {"Transactions.CallFunction": self.call_functions}},
                                            {"nested": {
                                                "path": "Transactions.InternalTxns",
                                                "query": {
                                                    "terms": {
                                                        "Transactions.InternalTxns.CallFunction": self.call_functions
                                                    }
                                                }
                                            }}
                                        ],
                                        "minimum_should_match": 1
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }

    def get_results(self):
        response = self.client.search(index=self.index_name, body=self.dsl_query, timeout=300)
        results = []
        for hit in response['hits']['hits']:
            inner_hits = hit.get('inner_hits', {}).get('Transactions', {}).get('hits', {}).get('hits', [])
            for tx in inner_hits:
                tx_src = tx.get('_source', {})
                tx_hash = tx_src.get('Hash')

                # 外部交易命中
                if tx_src.get('CallFunction') in self.call_functions:
                    results.append({
                        'CallFunction': tx_src.get('CallFunction'),
                        'CallParameter': tx_src.get('CallParameter'),
                        'ConAddress': tx_src.get('ConAddress'),
                        'FromAddress': tx_src.get('FromAddress'),
                        'ToAddress': tx_src.get('ToAddress'),
                        'Hash': tx_hash,
                        'Type': 'External',
                    })

                # 内部交易命中
                for internal in tx_src.get('InternalTxns', []):
                    if internal.get('CallFunction') in self.call_functions:
                        results.append({
                            'CallFunction': internal.get('CallFunction'),
                            'CallParameter': internal.get('CallParameter'),
                            'ConAddress': internal.get('ConAddress'),
                            'FromAddress': internal.get('FromAddress'),
                            'ToAddress': internal.get('ToAddress'),
                            'Hash': tx_hash,
                            'Type': 'Internal',
                            'InternalType': internal.get('Type', 'Unknown')
                        })
        return results


if __name__ == '__main__':
    with open('py_script/tools/propose_sig.json', 'r', encoding='utf-8') as f:
        sig_data = json.load(f)
        call_functions = [item['hex_signature'] for item in sig_data['results'] if 'hex_signature' in item]

    block_time = "2015"
    query = ProposalESQuery(block_time, call_functions)
    results = query.get_results()

    with open(f'py_script/tools/results{block_time}.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"查询结果已写入 results.json，共 {len(results)} 条记录。")