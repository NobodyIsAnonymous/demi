import os
import json
from typing import List, Dict, Set
from eth_utils import to_checksum_address

def load_results(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_unique_to_addresses(results: List[Dict]) -> Set[str]:
    return {item['ToAddress'] for item in results if 'ToAddress' in item and item['ToAddress']}

def lookup_contract_info(address: str, chain_id=1, base_dir="/Users/Lfear/Github_local/contracts") -> Dict:
    try:
        checksum = to_checksum_address(address)
    except Exception:
        return {
            "address": address,
            "info": None
        }

    filename = f"{base_dir}/contracts/{chain_id}/{checksum}.json"
    if not os.path.exists(filename):
        return {
            "address": address,
            "info": None
        }

    with open(filename, "r") as f:
        try:
            info = json.load(f)
        except Exception:
            info = None

    return {
        "address": address,
        "info": info
    }

def label_addresses(addresses: Set[str], base_dir: str, chain_id=1) -> List[Dict[str, str]]:
    labeled = []
    for addr in sorted(addresses):
        lookup = lookup_contract_info(addr, chain_id, base_dir)
        info = lookup['info']
        label = info.get("ContractName") if info and "ContractName" in info else ""
        labeled.append({
            "address": addr,
            "label": label
        })
    return labeled

def save_labeled_addresses(path: str, data: List[Dict[str, str]]):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    results_path = 'py_script/tools/results.json'
    base_contract_dir = '/Users/Lfear/Github_local/contracts'  # 可以按需修改
    output_path = 'py_script/tools/unique_to_addresses_labeled.json'
    chain_id = 1  # 以太坊主网

    results = load_results(results_path)
    unique_addrs = extract_unique_to_addresses(results)
    labeled_data = label_addresses(unique_addrs, base_contract_dir, chain_id)
    save_labeled_addresses(output_path, labeled_data)

    print(f"共提取 {len(unique_addrs)} 个唯一 ToAddress，已打标签并保存至 {output_path}")

if __name__ == '__main__':
    main()