import json
import os
from openai import OpenAI


# ======================
# Global Configuration
# ======================

# Prompt template: Find corresponding sentences
PROMPT_FIND_CORRESPONDING_SENTENCES = """
You need to analyze a governance proposal description and find corresponding sentences for each executed DSL action.

Given:
1. Governance proposal description (natural language)
2. List of executed DSL actions (extracted from execution trace)

Task:
For each DSL action, find the corresponding sentence or phrase in the description. If a DSL action has no corresponding content in the description, mark it as "not described".

Output JSON format:
{{
  "action_mapping": [
    {{
      "dsl_action": "specific DSL action", 
      "corresponding_text": "corresponding sentence or phrase in description",
      "is_described": true/false,
      "confidence": 0.8,  // confidence score (0-1)
      "reason": "explanation for the match"
    }}
  ],
  "overall_consistency": {{
    "described_actions": number,
    "total_actions": number,
    "consistency_rate": percentage,
    "summary": "overall consistency summary"
  }}
}}

Description:
{description}

DSL Actions:
{trace_dsl}
"""

# ======================
# Core Classes
# ======================

class ProposalConsistencyChecker:
    """
    Use existing trace DSL to directly find corresponding sentences in proposal description,
    determine whether each DSL action has a corresponding description, and thus determine overall consistency.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_functions_from_trace(self, trace_data) -> list:
        """Extract function names list from trace data"""
        functions = []
        
        if isinstance(trace_data, str):
            try:
                trace_data = json.loads(trace_data)
            except:
                return functions
        
        if isinstance(trace_data, dict) and "data" in trace_data:
            for call in trace_data.get("data", []):
                trace = call.get("trace", {})
                decoded = trace.get("decoded", {})
                if isinstance(decoded, dict) and "function" in decoded:
                    func_name = decoded["function"]
                    if func_name and func_name != "unknown":
                        functions.append(func_name)
        elif isinstance(trace_data, list):
            # Compatible with other trace formats
            for item in trace_data:
                if isinstance(item, dict):
                    if "function" in item:
                        functions.append(item["function"])
                    elif "name" in item:
                        functions.append(item["name"])
        
        return functions

    def convert_trace_to_dsl_local(self, trace_data) -> list:
        """Convert trace to DSL locally (1+3 optimization strategy), including parameter information"""
        if isinstance(trace_data, str):
            try:
                trace_data = json.loads(trace_data)
            except:
                return []
        
        dsl_actions = []

        if "data" not in trace_data or trace_data["data"] == []:
            return []

        if isinstance(trace_data, dict) and "data" in trace_data:
            for call in trace_data.get("data", []):
                trace = call.get("trace", {})
                decoded = trace.get("decoded", {})
                kind = trace.get("kind", "")

                if kind != "CALL":
                    continue

                if isinstance(decoded, dict) and "function" in decoded:
                    func_name = decoded["function"]
                    if func_name and func_name not in ["unknown", "execute", "executeBatch"]:
                        # Get basic DSL primitive
                        # primitive = mapping_cache.map_function_to_primitive(func_name)
                        
                        # Get parameter information
                        types = decoded.get("types", [])
                        values = decoded.get("values", [])
                        args = decoded.get("args", [])
                        
                        # Build enhanced DSL with original function name and parameter information
                        if types and values:
                            dsl_with_params = f"function:{func_name} | types:{types} | values:{values}"
                            dsl_actions.append(dsl_with_params)
                        elif args:
                            dsl_with_params = f"function:{func_name} | args:{args}"
                            dsl_actions.append(dsl_with_params)
                        else:
                            dsl_with_params = f"function:{func_name}"
                            dsl_actions.append(dsl_with_params)
        
        return dsl_actions

    def find_corresponding_sentences(self, description: str, trace_dsl: list) -> dict:
        """
        Find corresponding sentences in description based on trace DSL, determine consistency.
        
        Args:
            description: Proposal description text
            trace_dsl: List of executed DSL actions
            
        Returns:
            Dictionary containing action mapping and overall consistency analysis
        """
        if not trace_dsl:
            return {
                "action_mapping": [],
                "overall_consistency": {
                    "described_actions": 0,
                    "total_actions": 0,
                    "consistency_rate": 0.0,
                    "summary": "No executed DSL actions"
                }
            }
        
        prompt = PROMPT_FIND_CORRESPONDING_SENTENCES.format(
            description=description,
            trace_dsl=json.dumps(trace_dsl, indent=2, ensure_ascii=False)
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
        except Exception as e:
            if "response_format" in str(e):
                print(f"⚠️  Model {self.model} does not support JSON format, using plain text mode")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}]
                )
            else:
                raise e
                
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM response content is None")
        
        return json.loads(content)

    def check_consistency(self, description: str, trace_data) -> dict:
        """
        New consistency check method: directly find corresponding sentences in description using trace DSL
        
        Args:
            description: Proposal description
            trace_data: Execution trace data
            
        Returns:
            Consistency analysis result
        """
        # 1. Convert trace to DSL
        trace_dsl = self.convert_trace_to_dsl_local(trace_data)
        
        if not trace_dsl:
            return {
                "trace_dsl": [],
                "analysis": {
                    "action_mapping": [],
                    "overall_consistency": {
                        "described_actions": 0,
                        "total_actions": 0,
                        "consistency_rate": 0.0,
                        "summary": "No analyzable execution trace"
                    }
                }
            }
        
        # 2. Find corresponding sentences in description
        analysis = self.find_corresponding_sentences(description, trace_dsl)
        
        return {
            "trace_dsl": trace_dsl,
            "analysis": analysis
        }
    # Keep original compare method for backward compatibility (deprecated)
    def compare(self, description: str, trace: str) -> dict:
        """
        Original two-step process method (deprecated, kept for backward compatibility)
        Recommend using check_consistency method
        """
        print("⚠️  Warning: compare method is deprecated, please use check_consistency method")
        return self.check_consistency(description, trace)
    
if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set")
    checker = ProposalConsistencyChecker(api_key=api_key)

    description = """This proposal will transfer 1000 UNI to address 0x1234... for community grants,
    upgrade the proxy contract 0xProxy... to the new implementation contract 0xNewImpl...,
    and set the new governance parameter max_supply to 100000."""

    # Mock trace data
    trace_data = {
        "data": [
            {
                "trace": {
                    "kind": "CALL",
                    "decoded": {
                        "function": "transfer",
                        "types": ["address", "uint256"],
                        "values": ["0x1234...", "1000000000000000000000"]
                    }
                }
            },
            {
                "trace": {
                    "kind": "CALL", 
                    "decoded": {
                        "function": "upgradeTo",
                        "types": ["address"],
                        "values": ["0xNewImpl..."]
                    }
                }
            },
            {
                "trace": {
                    "kind": "CALL",
                    "decoded": {
                        "function": "setMaxSupply",
                        "types": ["uint256"],
                        "values": ["100000000000000000000000"]
                    }
                }
            }
        ]
    }

    result = checker.check_consistency(description, trace_data)

    print("=== Description ===")
    print(description)
    
    print("=== Trace DSL ===")
    print(json.dumps(result["trace_dsl"], indent=2, ensure_ascii=False))

    print("\n=== Consistency Analysis ===")
    print(json.dumps(result["analysis"], indent=2, ensure_ascii=False))
    
    print(f"\n=== Consistency Summary ===")
    analysis = result["analysis"]
    overall = analysis["overall_consistency"]
    print(f"Described actions: {overall['described_actions']}/{overall['total_actions']}")
    print(f"Consistency rate: {overall['consistency_rate']:.1f}%")
    print(f"Summary: {overall['summary']}")