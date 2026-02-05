import requests
import time
import json

def fetch_all_transactions(
    address,
    api_key,
    start_block=0,
    end_block=99999999,
    sort="asc",
    offset=100,
    save_to_file="py_script/etherscan_data/etherscan_transactions.json",
    delay=0.2
):
    """
    获取指定以太坊地址的所有交易记录并保存为 JSON 文件。

    参数:
    - address (str): 目标地址
    - api_key (str): Etherscan API 密钥
    - start_block (int): 起始区块
    - end_block (int): 结束区块
    - sort (str): 排序方式 ("asc" 或 "desc")
    - offset (int): 每页条数（最大100）
    - save_to_file (str): 输出文件名
    - delay (float): 每页请求之间的延时（秒）

    返回:
    - all_txs (list): 所有交易记录
    """

    base_url = "https://api.etherscan.io/v2/api"
    all_txs = []
    page = 1

    while True:
        params = {
            "chainid": 1,
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": sort,
            "apikey": api_key
        }

        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            break

        data = response.json()
        if data.get("status") != "1":
            print(f"⚠️ API Message: {data.get('message')}")
            break

        transactions = data.get("result", [])
        if not transactions:
            break

        all_txs.extend(transactions)
        print(f"✅ Page {page}: Retrieved {len(transactions)} transactions")

        if len(transactions) < offset:
            break

        page += 1
        time.sleep(delay)

    with open(save_to_file, "w") as f:
        json.dump(all_txs, f, indent=2)
    print(f"🎉 Total transactions saved: {len(all_txs)} to {save_to_file}")

    return all_txs

if __name__ == "__main__":
    my_address = "0x309a862bbC1A00e45506cB8A802D1ff10004c8C0"
    my_api_key = "XT28VFFFF8CFYISGIZ57V6Y1IR85UW8VUX"  # 替换成你的API KEY
    fetch_all_transactions(my_address, my_api_key)