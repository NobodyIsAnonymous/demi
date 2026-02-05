import json
import os
import pandas as pd
from typing import Any, Dict, List, Optional
from llm_simple_checker import judge_proposal
from pathlib import Path

def find_first_execute(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if node.get("function") == "execute":
        return node
    for child in node.get("children", []):
        result = find_first_execute(child)
        if result:
            return result
    return None

def remove_empty_and_none_fields(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: remove_empty_and_none_fields(v)
            for k, v in obj.items()
            if v is not None and v != []
        }
    elif isinstance(obj, list):
        cleaned_list = [remove_empty_and_none_fields(item) for item in obj]
        return [item for item in cleaned_list if item != {} and item != []]  # 进一步清除空元素
    else:
        return obj

def get_description_by_onchain_id(json_data: List[Dict[str, Any]], onchain_id: str) -> Optional[str]:
    try:
        proposals = json_data
    except (KeyError, TypeError):
        raise ValueError("Invalid JSON structure: missing expected keys.")

    for proposal in proposals:
        if proposal.get("onchainId") == str(onchain_id):
            return proposal.get("metadata", {}).get("description", None)

    return None  # 没有找到对应的 onchainId

def is_effective_children(children: list) -> bool:
    """判断children里是否有真正有用的内容节点"""
    if not children:
        return False
    for node in children:
        if node.get("type") == "revert":
            return False  # 有 revert 就直接无效
    for node in children:
        if any(
            v not in (None, "", [], {})
            for k, v in node.items()
            if k != "children"
        ):
            return True
        # 或递归判断更深层
        if is_effective_children(node.get("children", [])):
            return True
    return False

def extract_save_first_execute(proposal_id: int, slug: str, structured_data_path: str, execution_data_path: str) -> Optional[Dict[str, Any]]:
    trace_name = f"{slug}/Simulation-{proposal_id}.json"
    simulation_path = f"{structured_data_path}/{trace_name}"
    with open(simulation_path, "r") as f:
        trace_data = json.load(f)

    # 进入正确的children层级
    children_list = []
    if trace_data.get("children") and isinstance(trace_data["children"], list) and len(trace_data["children"]) > 0:
        children_list = trace_data["children"][0].get("children", [])

    executes = [node for node in children_list if node.get("function") == "execute"]

    execute_node = None
    for node in executes:
        if is_effective_children(node.get("children", [])):
            execute_node = node
            break

    if not execute_node:
        print("❌ No valid `execute` function (with effective children) found.")
        return None

    cleaned = remove_empty_and_none_fields(execute_node)
    if not os.path.exists(f"{execution_data_path}/{slug}"):
        os.makedirs(f"{execution_data_path}/{slug}")
    with open(f"{execution_data_path}/{slug}/Execution-{proposal_id}.json", "w") as f:
        json.dump(cleaned, f, indent=2)
    print(f"✅ Cleaned and saved to {execution_data_path}/{slug}/Execution-{proposal_id}.json")
    return cleaned

def get_description_by_proposal_id(slug: str, proposal_id: int, description_dir: str) -> Optional[str]:
    description_path = f"{description_dir}/tally_proposals_{slug}.json"
    with open(description_path, "r") as f:
        tally_data = json.load(f)
    return get_description_by_onchain_id(tally_data, str(proposal_id))

def extract_all_execution_traces_and_save(slug: str, simulation_files: List[int], structured_data_path: str, execution_data_path: str):
    """
    批量提取execution_trace并保存（你原本的逻辑）
    """
    for proposal_id in simulation_files:
        try:
            extract_save_first_execute(proposal_id, slug, structured_data_path, execution_data_path)
        except Exception as e:
            print(f"[warn] {slug} #{proposal_id} 提取execution_trace失败: {e}")

def judge_and_save_from_file(slug: str, simulation_files: List[int], description_dir: str, execution_data_path: str, out_dir: Path):
    """
    description 直接用 get_description_by_proposal_id, execution_trace 从本地文件读取
    """
    out_file = out_dir / f"{slug}_verdicts.json"
    exec_dir = os.path.join(execution_data_path, slug)
    with open(out_file, "w", encoding="utf-8") as fh:
        for proposal_id in simulation_files:
            exec_path = f"{exec_dir}/Execution-{proposal_id}.json"
            try:
                description = get_description_by_proposal_id(slug, proposal_id, description_dir)
                if description is None:
                    print(f"[warn] {slug} #{proposal_id} failed: description is None")
                    continue
            except Exception as e:
                print(f"[warn] {slug} #{proposal_id} 读取description失败: {e}")
                continue
            try:
                with open(exec_path, "r", encoding="utf-8") as f:
                    execution_trace = json.load(f)
            except Exception as e:
                print(f"[warn] {slug} #{proposal_id} 读取execution_trace失败: {e}")
                continue
            try:
                verdict_text = judge_proposal(description, execution_trace)
                print(f"[{slug} #{proposal_id}] {verdict_text}")
                head, *reason = verdict_text.split("\n", 1)
                malicious = head.strip().upper().endswith("YES")
                record = {
                    "slug": slug,
                    "proposal_id": proposal_id,
                    "malicious": malicious,
                    "verdict": head.strip(),
                    "reason": reason[0].strip() if reason else ""
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[warn] {slug} #{proposal_id} judge失败: {e}")
    print(f"✅ 完成judge并保存: {out_file}")

def get_simulation_files(slug: str, structured_data_path: str) -> List[int]:
    slug_dir = f"{structured_data_path}/{slug}"
    if not os.path.exists(slug_dir):
        print(f"⚠️ 目录不存在: {slug_dir}")
        return []
    simulation_files = []
    try:
        for file in os.listdir(slug_dir):
            if file.startswith("Simulation-") and file.endswith(".json"):
                proposal_id = file.replace("Simulation-", "").replace(".json", "")
                simulation_files.append(int(proposal_id))
    except Exception as e:
        print(f"❌ 读取目录失败 {slug_dir}: {e}")
    simulation_files = sorted(list(set(simulation_files)))
    return simulation_files

if __name__ == "__main__":
    # === 配置 ===
    structured_data_path  = "proxy_data/structured_traces"
    execution_data_path   = "proxy_data/execution_traces"
    description_dir       = "proxy_data/proposals"
    out_dir               = Path("proxy_data/verdicts")
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv("data_scripts/gov_eth.csv")
    slugs = df['slug'].tolist()
    # slugs = ["vesper-dao"]
    # 选择运行哪一步
    step = "judge"  # 可选: "get_execution_traces", "judge"
    for slug in slugs:
        simulation_files = get_simulation_files(slug, structured_data_path)
        if not simulation_files:
            continue
        if step == "get_execution_traces":
            extract_all_execution_traces_and_save(slug, simulation_files, structured_data_path, execution_data_path)
        elif step == "judge":
            judge_and_save_from_file(slug, simulation_files, description_dir, execution_data_path, out_dir)