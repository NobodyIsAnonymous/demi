# Example of running a transaction with Cast
# cast run -v -q 0xc5215eb1d9c63373a02a013105b9f6745df1c935bb5c25817423b947be8d3aea --rpc-url mainnet > trace_example.log

# Example of running a scripted transaction with Forge
# forge test --contracts ./src/test/2024-10/MorphoBlue_exp.sol -vvvv --evm-version shanghai > test_trace_example.log

# run all the tests and save the output to ../traces/<test_name>.log

import subprocess
import re
import json
import os
from eth_utils import to_checksum_address
from pathlib import Path
import pandas as pd

def lookup_contract_info(address, chain_id=1, base_dir="/Users/Lfear/Github_local/contracts"):
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

def is_exact_address(s):
    return isinstance(s, str) and re.fullmatch(r"0x[a-fA-F0-9]{40}", s)

def find_and_replace_in_string(s, chain_id=1, base_dir="/Users/Lfear/Github_local/contracts"):
    # 如果字符串是完整地址，直接结构化替换
    if is_exact_address(s):
        return lookup_contract_info(s, chain_id, base_dir)

    # 如果是其他字符串，例如包含地址参数的描述，保持原字符串（或你想分词提取也可以拓展）
    return s

def replace_addresses(obj, chain_id=1, base_dir="/Users/Lfear/Github_local/contracts"):
    if isinstance(obj, str):
        return find_and_replace_in_string(obj, chain_id, base_dir)

    elif isinstance(obj, list):
        return [replace_addresses(item, chain_id, base_dir) for item in obj]

    elif isinstance(obj, dict):
        return {
            key: replace_addresses(value, chain_id, base_dir)
            for key, value in obj.items()
        }

    else:
        return obj

def obtain_traces(slug, pid, test_path, save_path):

    if not os.path.exists(f"{save_path}/{slug}"):
        os.makedirs(f"{save_path}/{slug}")
    forge_cmd = f"forge test --match-path {test_path}/{slug}/Simulation-{pid}.t.sol -vvvv > {save_path}/{slug}/Simulation-{pid}.log"
    
    try:
        subprocess.run(forge_cmd, shell=True, check=True)
        print(f"Traces saved to {save_path}/{slug}/Simulation-{pid}.log")
    except Exception as e:
        print(f"Error running forge command: {e}")


def parse_trace_line(line):
    # 匹配缩进（每2或3个空格为一级）、框图符号（如 '├─' 或 '└─'）、调用信息
    match = re.match(r'(?P<indent>((  (│ |├─|└─)))*)(?P<content>.*)', line)
    if not match:
        return None
    
    indent = match.group('indent')
    indent_level = len(re.findall(r'  (│ |├─|└─)', indent))
    content = match.group('content').strip()
    
    return {
        'indent_level': indent_level,
        'content': content,
        'children': []
    }

def parse_trace_lines(trace_lines):
    root = {'content': 'root', 'children': []}
    node_stack = [root]

    for line in trace_lines:
        trace_info = parse_trace_line(line)
        if not trace_info:
            continue

        current_node = {
            'content': trace_info['content'],
            'children': []
        }

        # 确保缩进层级正确并将当前节点添加到其父节点的children中
        while len(node_stack) > trace_info['indent_level'] + 1:
            node_stack.pop()

        node_stack[-1]['children'].append(current_node)
        node_stack.append(current_node)

    return root

# 读取和处理第二个 Trace
def read_second_trace(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    trace_starts = [i for i, line in enumerate(lines) if line.startswith("Traces:")]
    if len(trace_starts) == 0:
        print(f"Error: 文件{file_path}中找不到 Trace")
        return
    if len(trace_starts) == 1:
        print(f"Warning: 文件{file_path}中只找到一个 Trace")
        start_index = trace_starts[0] + 1
    else:
        # 获取第二个 Trace 的内容，从 Traces: 开始到下一个空行之前
        start_index = trace_starts[1] + 1
        
    trace_lines = []
    for i in range(start_index, len(lines)):
        if lines[i].strip() == "":
            break
        trace_lines.append(lines[i][2:])
        
    return trace_lines

def extract_standard_call(content: str, result: dict) -> dict:
    try:
        gas_part = re.match(r"\[(\d+)]", content)
        if not gas_part:
            return None
        result["gas"] = int(gas_part.group(1))

        addr_func = re.search(r"\] ([0x\w]+)::(\w+)\(", content)
        if not addr_func:
            return None
        result["address"] = addr_func.group(1)
        result["function"] = addr_func.group(2)

        # 提取参数部分（从第一个 "(" 到最后一个 ")"）
        param_start = content.find("(", addr_func.end())
        param_end = content.rfind(")")
        result["parameters"] = content[param_start + 1 : param_end].strip()

        # 提取类型
        type_match = re.search(r"\) \[(\w+)\]$", content)
        result["type"] = type_match.group(1) if type_match else "call"
        return result
    except Exception:
        return None

def parse_trace_content(content: str) -> dict:
    """
    解析单行 trace 字符串 → dict
    支持:
      • 返回值、Stop
      • emit / topic / data
      • 标准 call 行 (含复杂参数)
    """
    result = {
        "gas": None,
        "address": None,
        "function": None,
        "parameters": None,
        "type": None,
        "return_value": None,
    }

    # 1) Return / Stop
    if content.startswith("← [Return] "):
        result["type"] = "return"
        result["return_value"] = content.split("← [Return] ", 1)[-1]
        return result
    if content.startswith("← [Stop]"):
        result["type"] = "stop"
        return result
    if content.startswith("← [Revert] "):
        result["type"] = "revert"
        result["return_value"] = content.split("← [Revert] ", 1)[-1]
        return result

    # 2) emit (high-level & low-level)
    if content.startswith("emit "):
        result["type"] = "emit"
        result["function"] = content[5:]
        return result
    if content.startswith("topic "):
        result["type"] = "emit_topic"
        return result
    if content.startswith("data: "):
        result["type"] = "emit_data"
        return result

    # 3) Standard call  (格式:  [gas] address::func(params) [opt_type])
    # 3.1 先匹配 gas / address / function，定位到第一个 "("
    head_match = re.match(r"\[(\d+)]\s+([0x\w]+)::(\w+)\(", content)
    if head_match:
        result["gas"]      = int(head_match.group(1))
        result["address"]  = head_match.group(2)
        result["function"] = head_match.group(3)

        # 3.2 参数: 从首个 "(" 到最后一个 ")"
        first_paren = content.find("(", head_match.end() - 1)
        last_paren  = content.rfind(")")
        if first_paren != -1 and last_paren != -1 and last_paren > first_paren:
            result["parameters"] = content[first_paren + 1 : last_paren].strip()

        # 3.3 调用类型: 形如 ") [delegatecall]"、") [staticcall]"
        type_match = re.search(r"\)\s\[(\w+)\]$", content)
        result["type"] = type_match.group(1) if type_match else "call"
        return result

    # fallback: 未识别行
    return result

def structure_trace(node):
    structured_node = parse_trace_content(node["content"])
    structured_node["children"] = [structure_trace(child) for child in node.get("children", [])]
    return structured_node    

def apply_address_replacement(structured_trace, chain_id=1, base_dir="/Users/Lfear/Github_local/contracts"):
    return replace_addresses(structured_trace, chain_id, base_dir)

def format_json(path):
    trace_lines = read_second_trace(path)
    if not trace_lines:
        return
    parsed_trace = parse_trace_lines(trace_lines)
    # save as json
    structured_trace = structure_trace(parsed_trace)
    readable_trace = apply_address_replacement(structured_trace)
    
    # check if the path exists, if not, create it
    structured_trace_path = path.replace('.log', '.json').replace('traces', 'structured_traces')
    structured_trace_dir = os.path.dirname(structured_trace_path)
    if not os.path.exists(structured_trace_dir):
        os.makedirs(structured_trace_dir)

    with open(structured_trace_path, 'w') as f:
        f.write(json.dumps(readable_trace, indent=4))
    print(f"Trace saved to {path.replace('.log', '.json')}")
    
def batch_format_json(read_path, slug):
    dir = f'{read_path}/{slug}'
    files = os.listdir(dir)
    for file in files:
        if file.endswith('.log'):
            format_json(f'{dir}/{file}')
    print("All traces processed successfully!")

def batch_run_tests(slugs, test_path, save_path):
    for slug in slugs:
        print(f"🔧 Processing {slug}...")
        source_path = Path(f"./proxy_data/generated/{slug}")
        dest_path = Path(f"{test_path}/{slug}")
        dest_path.mkdir(parents=True, exist_ok=True)

        simulation_files = source_path.glob("Simulation-*.t.sol")
        pid_pattern = re.compile(r'Simulation-(\d+)\.t\.sol$')

        linked_files = []
        has_output = False

        for f in simulation_files:
            match = pid_pattern.search(f.name)
            if not match:
                continue
            pid = int(match.group(1))
            link_target = dest_path / f.name
            try:
                os.symlink(f.resolve(), link_target)
                linked_files.append(link_target)
                obtain_traces(slug, pid, test_path=test_path, save_path=save_path)
                has_output = True  # 标记已经有输出
            except FileExistsError:
                print(f"⚠️  Skipping existing symlink: {link_target}")

        # 删除软链接
        for link in linked_files:
            try:
                link.unlink()
            except Exception as e:
                print(f"❌ Failed to delete symlink {link}: {e}")

        # 删除空目录
        try:
            if dest_path.exists() and dest_path.is_dir() and not any(dest_path.iterdir()):
                dest_path.rmdir()
                print(f"🧹 Removed empty directory {dest_path}")
        except Exception as e:
            print(f"❌ Failed to remove directory {dest_path}: {e}")

        # 只有在有输出的情况下才格式化日志
        trace_dir = Path(save_path) / slug
        if trace_dir.exists():
            batch_format_json(save_path, slug)
        else:
            print(f"⚠️ No output trace for {slug}, skipped formatting.")

    print("✅ All slugs processed successfully!")

if __name__ == '__main__':
    
    trace_path = './proxy_data/traces'
    test_path = f'test/generated'
    df = pd.read_csv("data_scripts/gov_eth.csv")
    slugs = df['slug'].tolist()
    slugs = ["vesper-dao"]
    batch_run_tests(slugs, test_path, trace_path)
    