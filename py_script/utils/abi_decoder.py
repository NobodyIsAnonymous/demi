import json
import os
from eth_abi.abi import decode as decode_abi
from eth_utils.hexadecimal import decode_hex

class AbiDecoder:
    def __init__(self, signature_json_path=None):
        if signature_json_path is None:
            signature_json_path = os.path.join(os.path.dirname(__file__), "../signature.json")
        self.signature_map = self._load_signature_map(signature_json_path)

    def _load_signature_map(self, json_path):
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Signature file not found: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            sig_list = json.load(f)
        sig_map = {}
        for item in sig_list:
            selector = item["hash"]
            signature = item["signature"]
            func_name = signature.split("(", 1)[0]
            # 解析参数类型
            if "(" in signature and ")" in signature:
                types_str = signature.split("(", 1)[1].rsplit(")", 1)[0]
                if types_str.strip() == "":
                    types = []
                else:
                    types = []
                    buf = ""
                    depth = 0
                    for c in types_str:
                        if c == "," and depth == 0:
                            types.append(buf.strip())
                            buf = ""
                        else:
                            if c == "(":
                                depth += 1
                            elif c == ")":
                                depth -= 1
                            buf += c
                    if buf.strip():
                        types.append(buf.strip())
            else:
                types = []
            sig_map[selector] = (func_name, types)
        sig_map["0x095ea7b3"] = ("approve", ["address", "uint256"])  # 特例处理常见函数
        return sig_map

    @staticmethod
    def split_calldata(calldata: str):
        """自动分离 selector 和参数部分"""
        if calldata.startswith("0x"):
            calldata = calldata[2:]
        if len(calldata) < 8:
            raise ValueError("calldata too short")
        sig = "0x" + calldata[:8]
        data = "0x" + calldata[8:]
        return sig, data

    def decode_transaction_input(self, hex_signature: str, calldata: str):
        if not calldata.startswith("0x"):
            return {"error": "Invalid calldata format (must start with 0x)"}
        if hex_signature not in self.signature_map:
            return {"error": f"Unsupported function selector: {hex_signature}"}
        func_name, abi_types = self.signature_map[hex_signature]
        try:
            calldata_bytes = decode_hex(calldata)
            # if len(calldata_bytes) < 4:
            #     return {"error": "Calldata too short"}
            encoded_args = calldata_bytes
            decoded = decode_abi(abi_types, encoded_args) if abi_types else ()
            return {
                "function": func_name,
                "types": abi_types,
                "values": self.parse_values(decoded)
            }
        except Exception as e:
            return {
                "function": func_name,
                "error": f"❌ Failed to decode: {e}"
            }

    @staticmethod
    def parse_values(values):
        parsed = []
        for v in values:
            if isinstance(v, (list, tuple)):
                parsed.append(AbiDecoder.parse_values(v))
            elif isinstance(v, bytes):
                parsed.append("0x" + v.hex())
            else:
                parsed.append(v)
        return parsed

# if __name__ == "__main__":
#     decoder = AbiDecoder()
#     example = "0x0825f38f0000000000000000000000008d5ed43dca8c2f7dfb20cf7b53cc7e593635d7b9000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000006160f36c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000024cfbd4885000000000000000000000000639572471f2f318464dc01066a56867130e45e2500000000000000000000000000000000000000000000000000000000"
#     example_sig, example_data = AbiDecoder.split_calldata(example)
#     result = decoder.decode_transaction_input(example_sig, example_data)
#     print(json.dumps(result, indent=2, ensure_ascii=False))