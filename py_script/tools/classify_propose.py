import json
import os
from collections import defaultdict, Counter


def load_data_by_year_range(base_dir, start_year, end_year):
    all_data = []
    for year in range(start_year, end_year + 1):
        file_path = os.path.join(base_dir, f"results{year}.json")
        if not os.path.exists(file_path):
            print(f"⚠️ 文件不存在: {file_path}，跳过")
            continue
        with open(file_path, "r") as f:
            try:
                data = json.load(f)
                all_data.extend(data)
                print(f"✅ 加载 {file_path}：{len(data)} 条记录")
            except json.JSONDecodeError:
                print(f"❌ 解析错误: {file_path}，跳过")
    print(f"\n📦 共合并 {len(all_data)} 条数据")
    return all_data

def group_by_hash(data):
    hash_groups = defaultdict(list)
    for entry in data:
        tx_hash = entry["Hash"]
        hash_groups[tx_hash].append(entry)
    return hash_groups

def count_group_sizes(hash_groups):
    size_counter = Counter()
    for calls in hash_groups.values():
        group_size = len(calls)
        size_counter[group_size] += 1
    return size_counter

from collections import defaultdict

def build_governance_clusters(hash_groups):
    # Step 1: map Hash -> ToAddresses
    hash_to_toaddrs = {}
    toaddr_to_hashes = defaultdict(set)

    # 👇 同时记录每个 hash 的 governance contract 地址（单个或列表）
    hash_to_governance_contract = {}

    for tx_hash, calls in hash_groups.items():
        # ------------------------------
        # 👇 查找 governance contract 地址
        external_calls = [c for c in calls if c["Type"] == "External"]
        internal_241_calls = [
            c for c in calls if c["Type"] == "Internal" and c.get("InternalType") == 241
        ]

        if external_calls:
            # 如果有 External，则使用其 ToAddress（只取第一个 External，假设是唯一主调用）
            gov_address = external_calls[0]["ToAddress"]
        elif internal_241_calls:
            # 否则，如果有 InternalType 241，则所有此类 ToAddress 作为候选
            gov_address = list({c["ToAddress"] for c in internal_241_calls})
        else:
            # 无法识别（设为 None）
            gov_address = None

        hash_to_governance_contract[tx_hash] = gov_address
        # ------------------------------

        # 👇 收集 ToAddress（原聚类逻辑）
        to_addrs = set(call["ToAddress"] for call in calls if "ToAddress" in call)
        hash_to_toaddrs[tx_hash] = to_addrs
        for addr in to_addrs:
            toaddr_to_hashes[addr].add(tx_hash)

    # Step 2: Union-Find setup
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        root_x, root_y = find(x), find(y)
        if root_x != root_y:
            parent[root_y] = root_x

    # 初始化并查集
    for tx_hash in hash_groups.keys():
        parent[tx_hash] = tx_hash

    # Step 3: union by shared ToAddress
    for addr, hashes in toaddr_to_hashes.items():
        hash_list = list(hashes)
        for i in range(1, len(hash_list)):
            union(hash_list[0], hash_list[i])

    # Step 4: 聚合 cluster
    clusters = defaultdict(list)
    for tx_hash in hash_groups.keys():
        root = find(tx_hash)
        clusters[root].append(tx_hash)

    # ✅ 返回两个字典：
    # - clusters: root_hash -> [member_hashes]
    # - hash_to_governance_contract: tx_hash -> contract address 或 list
    return clusters, hash_to_governance_contract

def invert_governance_map(hash_to_governance_contract):
    from collections import defaultdict

    gov_to_hashes = defaultdict(list)

    for tx_hash, gov in hash_to_governance_contract.items():
        if gov is None:
            continue
        # key must be string (dict key), handle both str and list
        key = gov if isinstance(gov, str) else str(sorted(gov))  # sort for consistency
        gov_to_hashes[key].append(tx_hash)

    return gov_to_hashes

def classify_by_callfunctions(hash_groups):
    pattern_to_hashes = defaultdict(list)

    for tx_hash, calls in hash_groups.items():
        callfuncs = set(call.get("CallFunction") for call in calls if "CallFunction" in call)
        key = str(sorted(callfuncs))  # 用字符串表示集合作为 dict 的 key
        pattern_to_hashes[key].append(tx_hash)

    return pattern_to_hashes

def main():
    base_dir = "py_script/tools/es_raw_proposals"  # 根目录
    start_year = 2015
    end_year = 2025  # 你可以修改为任意范围

    data = load_data_by_year_range(base_dir, start_year, end_year)
    hash_groups = group_by_hash(data)
    
    pattern_to_hashes = classify_by_callfunctions(hash_groups)

    print(f"共发现 {len(pattern_to_hashes)} 类不同的 CallFunction 组合：")
    for i, (pattern, tx_hashes) in enumerate(pattern_to_hashes.items(), 1):
        print(f"\n🧩 组合 {i}: {pattern}")
        print(f"包含 {len(tx_hashes)} 个 hash_group")
        if len(tx_hashes) <= 5:  # 只展示部分 hash
            for h in tx_hashes:
                print(f"  - {h}")

    # 可选：保存到文件
    with open("hash_groups_by_callfunction_pattern.json", "w") as f:
        json.dump(pattern_to_hashes, f, indent=2)
    
    
if __name__ == "__main__":
    main()