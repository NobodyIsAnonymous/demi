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
contract SimulationHashd8027fee is Test {
    address constant CALLER   = 0xE674a02341a0710FECB87B25DBC538cdA2648aDC;
    address constant GOVERNOR = 0xFbc3Ddda6B253d98591E60142969Eca767DF3d97;
    address constant VOTER1 = 0x48eab89c643a7E45D3a1029003F90536b2598008;
    address constant VOTER2 = 0xdcf37d8Aa17142f053AAA7dc56025aB00D897a19;
    address constant VOTER3 = 0xE674a02341a0710FECB87B25DBC538cdA2648aDC;
    address constant VOTER4 = 0xFAF8f164d853C24ee4abA543B8E02dEC0D6C6a13;
    address constant proposer = 0xE674a02341a0710FECB87B25DBC538cdA2648aDC;

    function setUp() public {}

    function testSimulateExecuteTxWithID() public {
        uint256 proposalStartBlock = 20318386;
        bytes32 proposalIdHash = 0xd8027feef8ddd2b7e03b4b04e988f7fa25825a58c3184277dd751c1639190e1d;

        address[] memory targets = new address[](1);
        targets[0] = 0x0b9e309d4662194e584730467AB46A8282a31403;
        uint256[] memory values = new uint256[](1);
        values[0] = 0;
        bytes[] memory calldatas = new bytes[](1);
        calldatas[0] = hex"8456cb59";
        bytes32 descriptionHash = 0x39bac03961c94df9e63a91b65388fd2d2bc5294c44b48b254a8c3802b4c50542;

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

        address[4] memory voters = [0x48eab89c643a7E45D3a1029003F90536b2598008, 0xdcf37d8Aa17142f053AAA7dc56025aB00D897a19, 0xE674a02341a0710FECB87B25DBC538cdA2648aDC, 0xFAF8f164d853C24ee4abA543B8E02dEC0D6C6a13];
        for (uint i; i < voters.length; ++i) {
            vm.startPrank(voters[i]);
            IGovernor(GOVERNOR).castVote(proposalIdHash, 1);
            vm.stopPrank();
        }

        vm.roll(block.number + IGovernor(GOVERNOR).votingPeriod() + 1);
        vm.warp(block.timestamp + IGovernor(GOVERNOR).votingPeriod() + 1);
        vm.prank(CALLER);

        try IGovernor(GOVERNOR).queue(proposalIdHash) {
            // default path
        } catch {
            IGovernor(GOVERNOR).queue(targets, values, calldatas, descriptionHash);
        }

        // vm.warp(block.timestamp + delay);
        vm.warp(block.timestamp + delay / 2);
        try IGovernor(GOVERNOR).execute(targets, values, calldatas, descriptionHash, proposer) {
            // executed successfully at delay/2
        } catch {
            vm.warp(block.timestamp + delay / 2); // move to full delay
            IGovernor(GOVERNOR).execute(targets, values, calldatas, descriptionHash, proposer);
        }
    }
}
