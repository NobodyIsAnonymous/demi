import requests
import json

# === 定义参数 ===
url = "http://127.0.0.1:7001/api/v2/simulate/txs"
headers = {"Content-Type": "application/json"}

# chain_id = 1
# tx_type = 2
# from_address = "0xEd8D51Bff7bD2B2B70556a36097F8fb1beb0DE6E"
# to_address = "0x3328f7f4a1d1c57c35df56bbf0c9dcafca309c49"
# value = "50000000000000000"
# gas = 450231
# gas_price = "21083654207"
# gas_tip_cap = "1083654207"
# gas_fee_cap = "15000000000"
# block_number = 21730893
# block_index = 55


chain_id = 1
tx_type = 2
from_address = "0x0459f41c5f09bf678d9c07331894de31d8c22255"
to_address = "0x408ed6354d4973f66138c91495f2f2fcbd8724c3"
value = "0"
gas = 5301971
gas_price = "5480280866"
gas_tip_cap = "1083654207"
gas_fee_cap = "15000000000"
block_number = 21730893
block_index = 55
data_field = (
    "0xfe0d94c1000000000000000000000000000000000000000000000000000000000000004f"
)

# === 构造请求体 ===
payload = {
    "ChainId": chain_id,
    "Config": {
        "Number": block_number,
        "Index": block_index
    },
    "Transactions": [
        {
            "Type": tx_type,
            "From": from_address,
            "GasPrice": gas_price,
            "Gas": gas,
            "To": to_address,
            "Value": value,
            "Data": data_field,
            "GasTipCap": gas_tip_cap,
            "GasFeeCap": gas_fee_cap
        }
    ]
}

# === 2. 发送请求 ===
response = requests.post(url, headers=headers, json=payload)

# === 3. 处理返回数据 ===
if response.status_code == 200:
    result = response.json()
    
    try:
        internal_txns = result['Transactions'][0].get('InternalTxns', [])
        
        # === 4. 保存到 JSON 文件 ===
        output_path = "internal_txns_output.json"
        with open(output_path, "w") as f:
            json.dump(internal_txns, f, indent=2)
        
        print(f"✅ Internal transactions saved to: {output_path}")
    except (KeyError, IndexError):
        print("❌ Cannot find Transactions[0].InternalTxns in response.")
else:
    print(f"❌ Request failed with status code: {response.status_code}")
    print(response.text)