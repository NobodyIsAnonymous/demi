# 重新导入依赖并重新执行之前的代码块
import json
import ast


# 修改后的 ContractESQuery 支持按合约地址和函数类型筛选，并保存结果为 JSON
class ContractESQuery:
    def __init__(self, block_time, call_functions, contract_address, host='192.168.3.146', port=9200):
        import os
        from opensearchpy import OpenSearch

        auth = (os.getenv('OPENSEARCH_USER'), os.getenv('OPENSEARCH_PASSWORD'))
        self.index_name = 'eth_block'
        self.block_time = block_time
        self.call_functions = call_functions
        self.contract_address = contract_address.lower()
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
                                    "gte": f"{self.block_time-10}-01-01",
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
                                        "Transactions.FromAddress",
                                        "Transactions.ToAddress",
                                        "Transactions.Logs",
                                        "Transactions.InternalTxns.CallFunction",
                                        "Transactions.InternalTxns.CallParameter",
                                        "Transactions.InternalTxns.FromAddress",
                                        "Transactions.InternalTxns.ToAddress",
                                        "Transactions.InternalTxns.Type"
                                    ],
                                    "size": 100
                                },
                                "query": {
                                    "bool": {
                                        "should": [
                                            {
                                                "bool": {
                                                    "must": [
                                                        {"terms": {"Transactions.CallFunction": self.call_functions}},
                                                        {"term": {"Transactions.ToAddress": self.contract_address}}
                                                    ]
                                                }
                                            },
                                            {
                                                "nested": {
                                                    "path": "Transactions.InternalTxns",
                                                    "query": {
                                                        "bool": {
                                                            "must": [
                                                                {"terms": {
                                                                    "Transactions.InternalTxns.CallFunction": self.call_functions
                                                                }},
                                                                {"term": {
                                                                    "Transactions.InternalTxns.ToAddress": self.contract_address
                                                                }}
                                                            ]
                                                        }
                                                    }
                                                }
                                            }
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

                if tx_src.get('CallFunction') in self.call_functions and tx_src.get('ToAddress', '').lower() == self.contract_address:
                    results.append({
                        'CallFunction': tx_src.get('CallFunction'),
                        'CallParameter': tx_src.get('CallParameter'),
                        'FromAddress': tx_src.get('FromAddress'),
                        'ToAddress': tx_src.get('ToAddress'),
                        'Hash': tx_hash,
                        'Type': 'External',
                        'Logs': tx_src.get('Logs', []),
                    })

                for internal in tx_src.get('InternalTxns', []):
                    if internal.get('CallFunction') in self.call_functions and internal.get('ToAddress', '').lower() == self.contract_address:
                        results.append({
                            'CallFunction': internal.get('CallFunction'),
                            'CallParameter': internal.get('CallParameter'),
                            'FromAddress': internal.get('FromAddress'),
                            'ToAddress': internal.get('ToAddress'),
                            'Hash': tx_hash,
                            'Type': 'Internal',
                            'InternalType': internal.get('Type', 'Unknown')
                        })
        return results

# 保存函数：按合约地址写入 JSON 文件
def save_txns_by_contract(results, contract_address):
    filename = f"{contract_address}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✅ 已保存 {len(results)} 条交易到 {filename}")

if __name__ == "__main__":
    # 示例调用
    year = 2025
    
    with open('proxy_data/ES_proposal_data/hex_signature/propose_sig.json', 'r', encoding='utf-8') as f:
        propose_sig_data = json.load(f)
        propose_signatures = [item['hex_signature'] for item in propose_sig_data['results'] if 'hex_signature' in item]
    
    with open('proxy_data/ES_proposal_data/hex_signature/execute_sig.json', 'r', encoding='utf-8') as f:
        execute_sig_data = json.load(f)
        execute_signatures = [item['hex_signature'] for item in execute_sig_data if 'hex_signature' in item]
    
    # contract = "0xe02640be68df835aa3327ea6473c02c8f6c3815a"
    contracts = []
    with open('proxy_data/ES_proposal_data/propose_profiles/gov_contract_to_hashes.json', 'r', encoding='utf-8') as f:
        contract_data = json.load(f)
        for key in contract_data.keys():
            # if key start with "[", we need transfer it into list
            if key.startswith("[") and key.endswith("]"):
                addresses = ast.literal_eval(key)
                for address in addresses:
                    contracts.append(address.lower())
            else:
                contracts.append(key.lower())
    
    for contract in contracts:
        print(f"Processing contract: {contract}")
        
        query = ContractESQuery(block_time=year, call_functions=propose_signatures, contract_address=contract)
        results = query.get_results()
        save_txns_by_contract(results, f"../../proxy_data/ES_proposal_data/contract_propose_execute/propose_{contract}")
        
        query = ContractESQuery(block_time=year, call_functions=execute_signatures, contract_address=contract)
        results = query.get_results()
        save_txns_by_contract(results, f"../../proxy_data/ES_proposal_data/contract_propose_execute/execute_{contract}")