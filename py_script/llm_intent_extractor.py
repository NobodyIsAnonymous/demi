from openai import OpenAI

client = OpenAI(api_key="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")
import json
from collections import Counter
import time

# === 配置部分 ===

SYMBOLIC_ACTIONS = [
    "transfer", "approve", "mint", "burn", "delegate", "upgrade"
]

ADDRESS_TYPES = [
    "project_address", "token_address", "admin_address", "user_address"
]

MAX_TRIES = 5
VOTE_THRESHOLD = 3

# === Prompt 构造 ===
def build_prompt(description):
    return f"""
You are an intent extraction engine for DAO proposals. You must extract the intended on-chain actions described in the proposal description.

Instructions:
- Only use the following symbolic actions: {', '.join(SYMBOLIC_ACTIONS)}
- Use only the following address placeholders: {', '.join(ADDRESS_TYPES)}
- Return output in strict JSON format as a list of calls.
- If the intent is unclear or ambiguous, return an empty list.

Example:
Input: "Transfer 100 ETH from treasury to the development team"
Output:
[
  {{
    "action": "transfer",
    "to": "project_address",
    "amount": "100 ETH"
  }}
]

Input: {description}
Output:
"""

# === 调用 ChatGPT API ===
def call_chatgpt(prompt, temperature=0.2):
    response = client.chat.completions.create(model="gpt-4",
    temperature=temperature,
    messages=[
        {"role": "system", "content": "You are a precise, deterministic proposal interpreter."},
        {"role": "user", "content": prompt}
    ])
    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
        return parsed
    except Exception:
        return None

# === 主执行逻辑 ===
def extract_intent_with_consensus(description):
    prompt = build_prompt(description)
    outputs = []

    for i in range(MAX_TRIES):
        result = call_chatgpt(prompt)
        if result:
            outputs.append(json.dumps(result, sort_keys=True))
        time.sleep(1.5)  # 稍微防止速率限制

    count = Counter(outputs)
    most_common, freq = count.most_common(1)[0]

    if freq >= VOTE_THRESHOLD:
        return json.loads(most_common)
    else:
        raise ValueError("Too much inconsistency in LLM output. Intent extraction failed.")

# === 示例使用 ===
if __name__ == "__main__":
    proposal_desc = """
    This proposal requests 250,000 USDC to be transferred to the developer treasury to fund ongoing V4 infrastructure.
    """
    try:
        intent = extract_intent_with_consensus(proposal_desc)
        print("🧠 Extracted Intent:")
        print(json.dumps(intent, indent=2))
    except ValueError as e:
        print("❌ Extraction failed:", e)