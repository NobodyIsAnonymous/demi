// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;
import "forge-std/Test.sol";

interface IGovernor {
    function execute(uint256) external;
    function execute(address[] calldata,uint256[] calldata,bytes[] calldata,bytes32) external;
    function execute(address[] calldata,uint256[] calldata,bytes[] calldata,bytes32,address) external;
    function queue(bytes32) external;
    function queue(uint256) external;
    function queue(address[] calldata,uint256[] calldata,bytes[] calldata,bytes32) external;
    function queue(address[] calldata,uint256[] calldata,bytes[] calldata,bytes32,address) external;
    function castVote(uint256, uint8) external;
    function castVote(uint256, bool) external;
    function castVote(bytes32, uint256) external;
    function timelock() external view returns(address);
    function votingDelay()  external view returns(uint256);
    function votingPeriod() external view returns(uint256);
}
interface ITimelock { function delay() external view returns(uint256); }
contract SimulationHash6b55ba86 is Test {
    address constant CALLER   = 0xC4813d8724Fba151cA102006208a573cA72c566C;
    address constant GOVERNOR = 0x1393f1b1B4eA06e2019ad2BFf498b1C46Ad5c706;
    address constant VOTER1 = 0xC4813d8724Fba151cA102006208a573cA72c566C;
    address constant proposer = 0x46F3524AF3c1F9F7480CF8f8611d95D72361BBFD;

    function setUp() public {}

    function testSimulateExecuteTxWithID() public {
        uint256 proposalStartBlock = 18410787;
        bytes32 proposalIdHash = 0x6b55ba86ec7accfad6dc031efebb10f496895d937139e50c5276ea1993bc6945;

        address[] memory targets = new address[](1);
        targets[0] = 0x7F4Ec49a66D773D63092dbD8FbCDFC71C9D9e2f3;
        uint256[] memory values = new uint256[](1);
        values[0] = 0;
        bytes[] memory calldatas = new bytes[](1);
        calldatas[0] = hex"d1bfda660000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000400000000000000000000000046f3524af3c1f9f7480cf8f8611d95d72361bbfd00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000078030c000000000000000000000000009a66502fcddbb2d13286a88691e18aaa8c71771600000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000078030c00000000000000000000000000dc9b96ea4966d063dd5c8dbaf08fe59062091b6d0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000006e9bb9000000000000000000000000000bc3807ec262cb779b38d65b38158acc3bfede100000000000000000000000000000000000000000000000000000000000000032000000000000000000000000000000000000000000000000000000006e9bb900";
        bytes32 descriptionHash = 0x7093596cf8d45036cdf70a36300fb664bc16e310fc220ae6c66cfb7e9a1abef0;

        vm.createSelectFork("http://127.0.0.1:8545", proposalStartBlock + 1);


        address TIMELOCK;
        uint256 delay;
        try IGovernor(GOVERNOR).timelock() returns (address t) {
            TIMELOCK = t;
            try ITimelock(TIMELOCK).delay() returns (uint256 d) {
                delay = d;
            } catch {
                delay = 172_8000;
            }
        } catch {
            TIMELOCK = address(0);
            delay = 172_8000;
        }


        vm.roll(proposalStartBlock + IGovernor(GOVERNOR).votingDelay() + 1);
        vm.warp(block.timestamp + IGovernor(GOVERNOR).votingDelay() + 1);

        address[1] memory voters = [0xC4813d8724Fba151cA102006208a573cA72c566C];
        for (uint i; i < voters.length; ++i) {
            vm.startPrank(voters[i]);
            IGovernor(GOVERNOR).castVote(proposalIdHash, 1);
            vm.stopPrank();
        }


        vm.roll(block.number + IGovernor(GOVERNOR).votingPeriod() + 1);
        vm.warp(block.timestamp + IGovernor(GOVERNOR).votingPeriod() + 1);
        vm.prank(CALLER);
        try IGovernor(GOVERNOR).queue(proposalIdHash) {
            // queued by id
        } catch {
            try IGovernor(GOVERNOR).queue(targets, values, calldatas, descriptionHash) {
                // queued by params
            } catch {
                try IGovernor(GOVERNOR).queue(targets, values, calldatas, descriptionHash, proposer) {
                } catch {
                    revert();
                }
            }
        }

        vm.warp(block.timestamp + delay / 2);
        bool executed = false;
        try IGovernor(GOVERNOR).execute(targets, values, calldatas, descriptionHash, proposer) {
            executed = true;
        } catch {
            vm.warp(block.timestamp + (delay + 1) / 2); // 补到 full delay
            IGovernor(GOVERNOR).execute(targets, values, calldatas, descriptionHash, proposer);
            executed = true;
        }
        require(executed, "execute failed");
    }
}
