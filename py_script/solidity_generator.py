#!/usr/bin/env python3
"""
gen_sol_dynamic_voters.py  ‒  根据 params 文件生成 Solidity 测试脚本
  • 自动将所有地址转换为 EIP-55 checksum
"""

import json, sys, textwrap
from pathlib import Path
from eth_utils import to_checksum_address, is_address
import pandas as pd

DATA_DIR = Path("./proxy_data/params")
OUT_DIR  = Path("./proxy_data/generated")
RPC_URL  = "http://192.168.0.91:8545"
ZERO     = "0x0000000000000000000000000000000000000000"

# ─────────────────────────────────────────
# Solidity 模板
# ─────────────────────────────────────────
SOL_HEADER = """\
// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;
import "forge-std/Test.sol";

interface IGovernor {
    function execute(address[] calldata,uint256[] calldata,bytes[] calldata,bytes32) external;
    function queue(address[] calldata,uint256[] calldata,bytes[] calldata,bytes32) external;
    function castVote(uint256,uint8) external;
    function castVote(uint256, bool) external;
    function queue(uint256) external;
    function execute(uint256) external;
    function timelock() external view returns(address);
    function votingDelay()  external view returns(uint256);
    function votingPeriod() external view returns(uint256);
}
interface ITimelock { function delay() external view returns(uint256); }
"""

SOL_BODY = """\
contract Simulation{ID} is Test {{
    address constant CALLER   = {CALLER};
    address constant GOVERNOR = {GOVERNOR};
{VOTER_CONSTS}

    function setUp() public {{}}

    function testSimulateExecuteTxWithID() public {{
        uint256 proposalStartBlock = {START};
        uint256 proposalId         = {PID};
        
        {TARGETS}
        {VALUES}
        {CALLDATAS}
        bytes32 descriptionHash = {DESC_HASH};

        vm.createSelectFork("{RPC}", proposalStartBlock + 1);
        address TIMELOCK = IGovernor(GOVERNOR).timelock();

        vm.roll(proposalStartBlock + IGovernor(GOVERNOR).votingDelay() + 1);

        address[{N}] memory voters = [{VOTER_ARRAY}];
        for (uint i; i < voters.length; ++i) {{
            vm.startPrank(voters[i]);
            try IGovernor(GOVERNOR).castVote(proposalId, 1) {{
                // ✅ default path
            }} catch {{
                // fallback to bool interface
                IGovernor(GOVERNOR).castVote(proposalId, true);
            }}
            vm.stopPrank();
        }}

        vm.roll(block.number + IGovernor(GOVERNOR).votingPeriod() + 1);
        vm.prank(CALLER);
        
        try IGovernor(GOVERNOR).queue(proposalId) {{
            // ✅ default path
        }} catch {{
            // fallback to detailed execute
            IGovernor(GOVERNOR).queue(targets, values, calldatas, descriptionHash);
        }}

        uint256 delay;

        try ITimelock(TIMELOCK).delay() returns (uint256 d) {{
            delay = d;
        }} catch {{
            delay = 172_8000;
        }}
        
        vm.warp(block.timestamp + delay);
        
        try IGovernor(GOVERNOR).execute(proposalId) {{
            // ✅ default path
        }} catch {{
            // fallback to detailed execute
            IGovernor(GOVERNOR).execute(targets, values, calldatas, descriptionHash);
        }}
    }}
}}
"""

# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────
def to_checksum(addr: str) -> str:
    """转换为 EIP-55 checksum; 无法解析则返回原字符串并提示"""
    raw = addr.lower()
    if raw == ZERO.lower():
        return ZERO
    if raw.startswith("eip155:"):
        raw = raw.split(":")[-1]
    if is_address(raw):
        return to_checksum_address(raw)
    print(f"[warn] 非法地址格式: {addr}")
    return addr  # fallback

# ─────────────────────────────────────────
# 生成逻辑
# ─────────────────────────────────────────
def gen_for_slug(slug: str, proposal_num: int = 0):
    path = DATA_DIR / f"{slug}.json"
    data = json.loads(path.read_text())

    caller = to_checksum(data.get("CALLER", ZERO))
    voters = [to_checksum(a) for a in data.get("VOTERS", [])]
    if not voters:
        print(f"[warn] {slug}: VOTERS empty, skipping")
        return

    voter_consts = "\n".join(
        f"    address constant VOTER{i+1} = {addr};"
        for i, addr in enumerate(voters)
    )
    voter_array = ", ".join(voters)
    n_voters    = len(voters)

    OUT_DIR.mkdir(exist_ok=True, parents=True)

    for prop in data["proposals"][:proposal_num]:
        pid   = prop["proposalId"]
        start = prop["proposalStartBlock"]
        gov   = to_checksum(prop["GOVERNOR"])
        
        targets = [to_checksum(t) for t in prop.get("targets", [])]
        values = [int(v) if v != "<nil>" else 0 for v in prop.get("values", [])]
        calldatas = prop.get("calldatas", [])
        desc_hash = prop.get("descriptionHash")

        sol_targets = f"address[] memory targets = new address[]({len(targets)});\n" + \
              "\n".join([f"        targets[{i}] = {to_checksum(target)};" for i, target in enumerate(targets)])
        sol_values = f"uint256[] memory values = new uint256[]({len(values)});\n" + \
                    "\n".join([f"        values[{i}] = {v};" for i, v in enumerate(values)])
        sol_calldatas = f"bytes[] memory calldatas = new bytes[]({len(calldatas)});\n" + \
                        "\n".join([f'        calldatas[{i}] = hex"{c[2:]}";' for i, c in enumerate(calldatas)])

        sol_code = SOL_HEADER + SOL_BODY.format(
            ID=pid,
            CALLER=caller,
            GOVERNOR=gov,
            VOTER_CONSTS=voter_consts,
            START=start,
            PID=pid,
            RPC=RPC_URL,
            N=n_voters,
            VOTER_ARRAY=voter_array,
            TARGETS=sol_targets,
            VALUES=sol_values,
            CALLDATAS=sol_calldatas,
            DESC_HASH=desc_hash
        )
        
        
        # 确保子目录存在
        slug_dir = OUT_DIR / slug
        slug_dir.mkdir(parents=True, exist_ok=True)
        out_file = slug_dir / f"Simulation-{pid}.t.sol"

        out_file.write_text(textwrap.dedent(sol_code))
        print(f"✅ generated {out_file}")

def batch_gen_for_slugs(slugs, proposal_num: int = 0):
    for slug in slugs:
        print(f"Processing {slug}...")
        gen_for_slug(slug, proposal_num)
    print("All Solidity files generated successfully!")

if __name__ == "__main__":
    # read all the files' name from DATA_DIR as slugs
    df = pd.read_csv("data_scripts/gov_eth.csv")
    slugs = df['slug'].tolist()
    batch_gen_for_slugs(slugs, proposal_num=5)
    
    
    # gen_for_slug("3t-governance")