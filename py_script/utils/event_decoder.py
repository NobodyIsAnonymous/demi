import json
import requests
import re
from eth_utils import decode_hex
from eth_abi.codec import ABICodec
from eth_abi.registry import registry
from eth_abi.grammar import parse
from eth_abi.abi import decode as decode_abi
import requests
from requests.adapters import HTTPAdapter, Retry

# 构造支持重试的 requests Session
session = requests.Session()
retries = Retry(
    total=5,                # 总重试次数
    backoff_factor=0.5,     # 重试间隔：0.5s, 1s, 2s...
    status_forcelist=[502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("http://", adapter)
session.mount("https://", adapter)

# 本地缓存文件路径
LOCAL_SIGNATURE_CACHE = "/Users/Lfear/Github_local/proposal_simulator/py_script/utils/topic_signature_cache_from_local.json"

# 载入本地缓存
try:
    with open(LOCAL_SIGNATURE_CACHE, "r") as f:
        local_cache = json.load(f)
except Exception as e:
    print(f"[Warning] Failed to load local signature cache: {e}")
    local_cache = {}

codec = ABICodec(registry)  # 新版本中使用 codec 实例

def get_event_signature(topic_hash: str):
    # 优先查本地缓存
    if topic_hash in local_cache:
        return local_cache[topic_hash]
    
    url = f"https://www.4byte.directory/api/v1/event-signatures/?hex_signature={topic_hash}"
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            return results[0]["text_signature"]
    except Exception as e:
        print(f"[Error] 4byte lookup failed: {e}")
    return None

def parse_types_from_signature(signature):
    match = re.match(r"(\w+)\((.*)\)", signature)
    if not match:
        raise ValueError(f"Invalid signature format: {signature}")
    event_name, type_str = match.groups()
    parsed = parse(f"({type_str})").components
    return event_name, [c.to_type_str() for c in parsed]

def decode_event_log(topic_hash, topics, data_hex):
    signature = get_event_signature(topic_hash.lower())
    if not signature:
        return {"error": f"❌ Could not resolve event signature for {topic_hash}"}

    try:
        event_name, all_types = parse_types_from_signature(signature)

        indexed_count = len(topics) - 1
        indexed_types = all_types[:indexed_count]
        non_indexed_types = all_types[indexed_count:]

        # Decode indexed topics[1:]
        indexed_values = []
        for i, t in enumerate(indexed_types):
            try:
                value = decode_abi([t], decode_hex(topics[i + 1]))[0]
                indexed_values.append(str(value))
            except Exception as e:
                indexed_values.append(f"[decode_error: {e}]")

        # Decode data
        try:
            data = decode_hex(data_hex)
            decoded_data = codec.decode(non_indexed_types, data)
            non_indexed_values = [str(v) for v in decoded_data]
        except Exception as e:
            non_indexed_values = [f"[decode_error: {e}]"]

        return {
            "event": event_name,
            "signature": signature,
            "indexed_types": indexed_types,
            "indexed_values": indexed_values,
            "non_indexed_types": non_indexed_types,
            "non_indexed_values": non_indexed_values
        }

    except Exception as e:
        return {
            "event": signature,
            "error": f"❌ Failed to decode: {e}"
        }