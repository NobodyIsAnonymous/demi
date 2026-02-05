// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import "forge-std/Script.sol";

interface IGovernor {
    // function propose(address[] memory targets, uint256[] memory values, bytes[] memory calldatas, string memory description) external returns (uint256);
    function queue(address[] targets,uint256[] values,bytes[] calldatas,bytes32 descriptionHash);
    function execute(address[] targets,uint256[] values,bytes[] calldatas,bytes32 descriptionHash);
    // function state(uint256 proposalId) external view returns (uint8);
    // function proposalSnapshot(uint256 proposalId) external view returns (uint256);
    // function proposalDeadline(uint256 proposalId) external view returns (uint256);
}

contract GovernanceScript is Script {
    address governor = 0x1234567890abcdef1234567890abcdef12345678; // 替换成你的 Governor 地址
    address targetContract = 0xfeedfacefeedfacefeedfacefeedfacefeedface; // 你希望 propose 调用的目标合约

    function run() external {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerKey);

        IGovernor gov = IGovernor(governor);

        address ;
        uint256 ;
        bytes ;

        // 示例调用：目标合约的某个函数（如 setValue(uint256)）
        targets[0] = targetContract;
        values[0] = 0;
        calldatas[0] = abi.encodeWithSignature("setValue(uint256)", 42);

        string memory description = "Proposal #1: set value to 42";
        bytes32 descriptionHash = keccak256(bytes(description));

        gov.queue(targets, values, calldatas, descriptionHash);

        vm.roll(block.number + 1);
        vm.warp(block.timestamp + 3 days); // timelock delay

        // 执行
        gov.execute(targets, values, calldatas, descriptionHash);

        vm.stopBroadcast();
    }
}