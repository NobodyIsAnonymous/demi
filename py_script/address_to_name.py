import os
import json
from eth_utils import to_checksum_address

def lookup_contract_info(address, chain_id=1, base_dir="/Users/Lfear/Github_local/contracts"):
    checksum = to_checksum_address(address)
    filename = f"{base_dir}/contracts/{chain_id}/{checksum}.json"
    if not os.path.exists(filename):
        return None
    with open(filename, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    # Example usage
    info = lookup_contract_info("0x1a9c8182c09f50c8318d769245bea52c32be35bc")
    print(info)
    # print(info["project"], info["name"])  # Dai Stablecoin DAI