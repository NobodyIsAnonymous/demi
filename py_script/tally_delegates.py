import requests
import json

# === GraphQL 端点 ===
url = "https://api.tally.xyz/query"  # Tally 的 GraphQL endpoint

# === GraphQL 查询语句 ===
query = """
query Delegates($input: DelegatesInput!) {
  delegates(input: $input) {
    nodes {
      ... on Delegate {
        ...DelegateFragment
      }
    }
    pageInfo {
      firstCursor
      lastCursor
      count
    }
  }
}

fragment DelegateFragment on Delegate {
  id
  account {
    id
    address
  }
  votesCount
  token {
    id
    type
    name
    symbol
    supply
  }
}
"""

# === 变量部分 ===
variables = {
    "input": {
        "filters": {
            "governorId": "eip155:1:0x408ED6354d4973f66138C91495F2f2FCbd8724C3"
        },
        "sort": {
            "isDescending": True,
            "sortBy": "votes"
        }
    }
}

# === 请求头（API Key） ===
headers = {
    "Content-Type": "application/json",
    "Api-Key": "8a5c96ce21e6bf3da8cfe3ca51277340cd5fc1ee8bc775e13269d412ec6c73e8"
}

# === 构造请求体 ===
payload = {
    "query": query,
    "variables": variables
}

# === 发送请求 ===
response = requests.post(url, json=payload, headers=headers)

# === 检查响应 & 保存到文件 ===
if response.status_code == 200:
    data = response.json()
    with open("py_script/etherscan_data/tally_delegates.json", "w") as f:
        json.dump(data, f, indent=2)
    print("✅ 成功保存响应数据到 py_script/etherscan_data/tally_delegates.json")
else:
    print(f"❌ 请求失败，状态码: {response.status_code}")
    print(response.text)