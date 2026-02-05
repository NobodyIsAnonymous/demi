#!/usr/bin/env python3
"""
check_proposal_llm.py
Quick POC: use GPT to judge if proposal execution is malicious.

Assumes you already have:
    description = get_description_by_proposal_id(...)
    execution_trace = extract_save_first_execute(...)

Simply import this module, or call main().
"""

import json
import os
import textwrap
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from dotenv import load_dotenv

load_dotenv()

def summarize_trace(node: dict, depth: int = 2, indent: int = 0) -> str:
    """
    Recursively stringify trace up to `depth` for prompt brevity.
    """
    pad = "  " * indent
    line = f"{pad}- {node.get('function')}({node.get('parameters')}) @ {node.get('address', {}).get('info', {}).get('name','address')}"
    if depth == 0 or not node.get("children"):
        return line
    children = "\n".join(
        summarize_trace(c, depth - 1, indent + 1) for c in node["children"][:3]
    )
    return f"{line}\n{children}"

def summarize_trace_minified(node: dict, depth: int = 20, length: int = 20) -> dict:
    """
    Recursively trim the execution trace to a compact, relevant structure.
    Includes function name, parameters, address name, and up to 3 children.
    """
    result = {
        "function": node.get("function"),
        "parameters": node.get("parameters"),
        "address": node.get("address", {}).get("info", {}).get("name", "address"),
    }
    if depth > 0 and node.get("children"):
        result["children"] = [
            summarize_trace_minified(child, depth - 1)
            for child in node["children"][:length]
        ]
    return result

# ─────────────────────────────
# ❸ Build LLM prompt messages
# ─────────────────────────────
def build_messages(description: str, execution_trace: dict):
    trace_summary_obj = summarize_trace_minified(execution_trace)
    trace_summary_str = json.dumps(trace_summary_obj, separators=(",", ":"), ensure_ascii=False)

    system_prompt = (
        "You are a smart contract auditor. "
        "Given a DAO proposal's description and its simulated execution trace, "
        "determine whether the execution contains malicious or hidden behavior "
        "not mentioned in the description.\n"
        "You will be provided a compressed JSON version of the trace.\n"
        "Respond in exactly this format:\n"
        "MALICIOUS: YES | SUSPICIOUS | NO\n"
        "Reason: <concise explanation, max 150 words>\n"
    )

    user_prompt = f"""\
### Description
{description}

### Compressed Execution Trace (JSON)
{trace_summary_str}
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": textwrap.dedent(user_prompt)},
    ]

# ─────────────────────────────
# ❹ Main judgment function
# ─────────────────────────────
def judge_proposal(description: str, execution_trace: dict, model="gpt-4o-mini"):
    messages = build_messages(description, execution_trace)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        max_tokens=300
    )
    return resp.choices[0].message.content.strip()