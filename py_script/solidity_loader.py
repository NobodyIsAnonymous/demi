#!/usr/bin/env python3
"""
read_params.py  ‒  解析 DAO 数据文件
  • CALLER  ——  Gov-{slug}.json              （methodId == 0xfe0d94c1 的交易 from）
  • VOTERS  ——  tally_delegates_{slug}.json  （前 10 个 node.account.address）
  • proposals[]  ——  tally_proposals_{slug}.json
       └─ { GOVERNOR, proposalStartBlock, proposalId }
"""

import json, sys
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
from web3 import Web3

DATA_DIR = Path("./proxy_data")      # 如有需要自行修改

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)    # 顶层应为 list[dict]

def get_caller(slug: str) -> str:
    """
    从 etherscan_data/Gov-{slug}.json 中查找 functionName
    含 'execute' / 'queue' / 'cancel' 的交易，返回其 'from' 地址。
    未找到或异常时返回零地址。
    """
    ZERO_ADDR = "0x0000000000000000000000000000000000000000"
    try:
        gov_path = DATA_DIR / f"etherscan_data/Gov-{slug}.json"
        tx_list = load_json(gov_path)  # 顶层 list[dict]

        KEYWORDS = ("execute", "queue", "cancel")
        for tx in tx_list:
            fn = tx.get("functionName", "").lower()
            if any(kw in fn for kw in KEYWORDS):
                return tx.get("from", ZERO_ADDR)

    except Exception as e:
        # 若需要可打印或记录: print(f"warn: {e}")
        pass

    return ZERO_ADDR

def get_top_voters(slug: str, limit: int = 10) -> List[str]:
    delegates_path = DATA_DIR / f"delegates/tally_delegates_{slug}.json"
    nodes = load_json(delegates_path)      # 顶层 list
    addrs = [
        node.get("account", {}).get("address")
        for node in nodes
        if node.get("account") and node["account"].get("address")
    ]
    return addrs[:limit]

def get_proposal_params(slug: str) -> List[Dict[str, Any]]:
    prop_path = DATA_DIR / f"proposals/tally_proposals_{slug}.json"
    nodes = load_json(prop_path)           # 顶层 list
    out = []
    for node in nodes:
        executable_calls = node.get("executableCalls", [])
        targets = [call["target"] for call in executable_calls]
        calldatas = [call["calldata"] for call in executable_calls]
        values = [int(call["value"]) if call["value"] != "<nil>" else 0 for call in executable_calls]
        description = node["metadata"]["description"]
        description_hash = Web3.keccak(text=description).hex()

        out.append(
            {
                "proposalId":       int(node["onchainId"]),
                "proposalStartBlock": int(node["block"]["number"]),
                "GOVERNOR":           node["governor"]["id"],
                "targets":            targets,
                "calldatas":          calldatas,
                "values":             values,
                "description":        description,
                "descriptionHash":    description_hash,
            }
        )
    return out

def load_params(slug: str):
    caller   = get_caller(slug)
    voters   = get_top_voters(slug)
    proposals = get_proposal_params(slug)

    result = {
        "CALLER": caller,
        "VOTERS": voters,
        "proposals": proposals,
    }
    return result

if __name__ == "__main__":
    df = pd.read_csv("data_scripts/gov_eth.csv")
    slugs = df['slug'].tolist()
    
    for slug in slugs:
        print(f"Processing {slug}...")
        result = load_params(slug)
        
        output_path = DATA_DIR / f"params/{slug}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)