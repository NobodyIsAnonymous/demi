import requests
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import ast

def fetch_all_transactions(
    address,
    api_key,
    start_block=0,
    end_block=99999999,
    sort="asc",
    offset=100,
    delay=0.2,
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
    session = requests.Session()
    
    # 加入重试机制
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False,
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))

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

        try:
            response = session.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.SSLError as ssl_err:
            print(f"SSL ERROR ❌: {ssl_err}")
            break
        except Exception as e:
            print(f"Other Error ❌: {e}")
            break


        data = response.json()
        if data.get("status") != "1":
            print(f"⚠️ API Message: {data.get('message')}")
            break

        transactions = data.get("result", [])
        if not transactions:
            break

        all_txs.extend(filter_non_vote_transactions(transactions))
        print(f"✅ Page {page}: Retrieved {len(transactions)} transactions")

        if len(transactions) < offset:
            break

        page += 1
        time.sleep(delay)

    print(f"🎉 Total transactions retrieved: {len(all_txs)}")

    return all_txs

def filter_non_vote_transactions(transactions):
    """
    从交易列表中过滤出 functionName 不含 'vote' 的交易。

    参数:
    - transactions (list): 包含交易记录的列表

    返回:
    - filtered (list): functionName 不含 'vote' 的交易记录
    """
    filtered = [
        tx for tx in transactions
        if 'functionName' in tx and 'vote' not in tx['functionName'].lower()
    ]
    return filtered

# 示例：从 JSON 文件加载数据并进行过滤
if __name__ == "__main__":
    
    input_file = "data_scripts/gov_eth.csv"
    
    # load csv into dataframe
    df = pd.read_csv(input_file)
    output_file_name = []
    project_address = []
    # for each row, load the slug and governorIds into ouput_file_name and project_address
    output_file_name = df['slug'].tolist()
    project_addresses = df['governorIds'].apply(ast.literal_eval)
    my_api_key = "XT28VFFFF8CFYISGIZ57V6Y1IR85UW8VUX"  # 替换成你的API KEY
    
    for i in range(len(output_file_name)):
        output_file = f"py_script/etherscan_data/Gov-{output_file_name[i]}.json"
        project_address = project_addresses[i][0].split(':')[2]
    
        non_vote_txs = fetch_all_transactions(project_address, my_api_key)

        with open(output_file, "w") as f:
            json.dump(non_vote_txs, f, indent=2)

        print(f"✅ Saved {len(non_vote_txs)} non-vote transactions to {output_file}")