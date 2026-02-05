// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;
import "forge-std/Test.sol";

interface IGovernor {
    function execute(uint256) external;
    function execute(address[] calldata,uint256[] calldata,bytes[] calldata,bytes32) external;
    function execute(address[] calldata,uint256[] calldata,bytes[] calldata,bytes32,address) external;
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
contract Simulation25 is Test {
    address constant CALLER   = 0xc8C8B126Fb3e69A03fE11F28c64059fcEB946179;
    address constant GOVERNOR = 0x3e352d95B709072035e488e15863EC716cA20240;
    address constant VOTER1 = 0x23B7B697fcF65df2f2F685691Dcbe31ffE5F4856;
    address constant VOTER2 = 0x75A07724D23E623b4fAEE220f2DDb4EAC3C97F0a;
    address constant VOTER3 = 0xb325dDE06383A3BA9Cf487D541180629B4326c7a;
    address constant VOTER4 = 0xbE7AC4A27892dF47AF9B56a046FAbfdEDD51D9e0;
    address constant VOTER5 = 0xeDd01bBB5Cd0FbA7dc4221BfBE0C4dC5D4EDD43D;
    address constant proposer = 0xeDd01bBB5Cd0FbA7dc4221BfBE0C4dC5D4EDD43D;

    function setUp() public {}

    function testSimulateExecuteTxWithID() public {
        uint256 proposalStartBlock = 14428475;
        uint256 proposalId = 25;

        address[] memory targets = new address[](1);
        targets[0] = 0x010CacCF546de952c5591B7018340549bE2eb641;
        uint256[] memory values = new uint256[](1);
        values[0] = 0;
        bytes[] memory calldatas = new bytes[](1);
        calldatas[0] = hex"000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48000000000000000000000000000000000000000000000000000000012a05f200000000000000000000000000000000000000000000005d480d811b8597e4bc98000000000000000000000000000000000000000000008bec1441a94863d71ae4000000000000000000000000fe3e6a25e6b192a42a44ecddcd13796471735acf00000000000000000000000000000000000000000000000000000000000000c000000000000000000000000000000000000000000000000000000000000000e82e95b6c8000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48000000000000000000000000000000000000000000000000000000012a05f200000000000000000000000000000000000000000000005d480d811b8597e4bc980000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000200000000000000003b6d034020e95253e54490d8d30ea41574b24f741ee7020100000000000000003b6d03407937619a9bd1234a303e4fe752b8d4f37d40e20ccfee7c08000000000000000000000000000000000000000000000000";
        bytes32 descriptionHash = 0xafd8bc0df6dc3e40376e7d736bc1733293615928dcb5624a0ce6ad4e8069a425;

        vm.createSelectFork("http://127.0.0.1:8545", proposalStartBlock + 1);
        address TIMELOCK = IGovernor(GOVERNOR).timelock();

        vm.roll(proposalStartBlock + IGovernor(GOVERNOR).votingDelay() + 1);

        address[5] memory voters = [0x23B7B697fcF65df2f2F685691Dcbe31ffE5F4856, 0x75A07724D23E623b4fAEE220f2DDb4EAC3C97F0a, 0xb325dDE06383A3BA9Cf487D541180629B4326c7a, 0xbE7AC4A27892dF47AF9B56a046FAbfdEDD51D9e0, 0xeDd01bBB5Cd0FbA7dc4221BfBE0C4dC5D4EDD43D];
        for (uint i; i < voters.length; ++i) {
            vm.startPrank(voters[i]);
            IGovernor(GOVERNOR).castVote(proposalId, 1);
            vm.stopPrank();
        }

        vm.roll(block.number + IGovernor(GOVERNOR).votingPeriod() + 1);
        vm.prank(CALLER);

        try IGovernor(GOVERNOR).queue(proposalId) {
            // ✅ default path
        } catch {
            IGovernor(GOVERNOR).queue(targets, values, calldatas, descriptionHash);
        }

        uint256 delay;
        try ITimelock(TIMELOCK).delay() returns (uint256 d) {
            delay = d;
        } catch {
            delay = 172_8000;
        }

        vm.warp(block.timestamp + delay);

        IGovernor(GOVERNOR).execute(proposalId);
    }
}
