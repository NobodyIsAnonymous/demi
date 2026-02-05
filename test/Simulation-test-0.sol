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
contract SimulationHash5d5985fc is Test {
    address constant CALLER   = 0x24e4dB5511B7a1F173cAE8f3EdA59D0294BD2EeB;
    address constant GOVERNOR = 0x5a2aAeEd954813E74DA7278438851ba5b679fF0a;
    address constant VOTER1 = 0x24e4dB5511B7a1F173cAE8f3EdA59D0294BD2EeB;
    address constant VOTER2 = 0x9f4e281202d019A8Ab8A444713C9571A62474Da4;
    address constant proposer = 0x9f4e281202d019A8Ab8A444713C9571A62474Da4;

    function setUp() public {}

    function testSimulateExecuteTxWithID() public {
        uint256 proposalStartBlock = 16880699;
        bytes32 proposalIdHash = 0x5d5985fc007981ec21c09dee71b39dccbb08a783717f041982f83f38e5cde626;

        address[] memory targets = new address[](6);
        targets[0] = 0x9E7D957D750447b140d8b20f45f651985Ddd1478;
        targets[1] = 0xeb1E38eb8740b42c8D6E712d2654fE981B19f140;
        targets[2] = 0x5a2aAeEd954813E74DA7278438851ba5b679fF0a;
        targets[3] = 0x5a2aAeEd954813E74DA7278438851ba5b679fF0a;
        targets[4] = 0x9E7D957D750447b140d8b20f45f651985Ddd1478;
        targets[5] = 0x9E7D957D750447b140d8b20f45f651985Ddd1478;
        uint256[] memory values = new uint256[](6);
        values[0] = 0;
        values[1] = 0;
        values[2] = 0;
        values[3] = 0;
        values[4] = 0;
        values[5] = 0;
        bytes[] memory calldatas = new bytes[](6);
        calldatas[0] = hex"8456cb59";
        calldatas[1] = hex"e735b48a000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000002644e6f756e62657273206973206261736564206f6e20646174657320746861742063616e206265206d656d6f7261626c6520696e206164646974696f6e20746f2044414f204e6f756e732e20537461727420616e20617274697374696320616e6420636f6c6c6563746976652070726f6365737320696e2074686520636f6d6d756e6974792e204d616e79206f662075732068617665206265656e207374726f6e676c7920756e6974656420627920676c617373657320616e642073696e63652074686520626567696e6e696e67206f6620746869732070726f6a656374207468652064617465732e20536f20796f75206172652070617274206f66206f757220636f6d6d756e6974792e204e6f77206f7572206f6e6c79207175657374696f6e2069732c20776861742064617465732077696c6c20626520796f7572732e5c6e5c6e576520686176652061206c6f74206f6620656e6572677920746f206d616b65207468697320636f6d6d756e6974792067726f7720616e642061626f766520616c6c20636f6e747269627574652e2054686174206973207768792077652061736b20796f7520746f206a6f696e206f75722074656c656772616d2e20416c736f207468617420796f752068656c7020757320746f20776f726b206f6e207468652070726f6a6563742e5c6e5c6e54656c656772616d3a2068747470733a2f2f742e6d652f6e6f756e626572735c6e5c6e2d2d2d2d2d5465616d2d2d2d2d5c6e6573646f7467653a2068747470733a2f2f6e662e74642f6573646f7467655c6e78787461726878783a2068747470733a2f2f6e662e74642f78787461726878785c6e5c6e00000000000000000000000000000000000000000000000000000000";
        calldatas[2] = hex"ef00ef430000000000000000000000000000000000000000000000000000000000015180";
        calldatas[3] = hex"63d61a190000000000000000000000000000000000000000000000000000000000000708";
        calldatas[4] = hex"f6be71d10000000000000000000000000000000000000000000000000000000000015180";
        calldatas[5] = hex"3f4ba83a";
        bytes32 descriptionHash = 0x5aa57d95b5b9b26dbdab87acfe66a98b4cd7258bb1e405fabad2c8466ce3e875;

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

        vm.warp(block.timestamp + IGovernor(GOVERNOR).votingDelay() + 1);

        address[2] memory voters = [0x24e4dB5511B7a1F173cAE8f3EdA59D0294BD2EeB, 0x9f4e281202d019A8Ab8A444713C9571A62474Da4];
        for (uint i; i < voters.length; ++i) {
            vm.startPrank(voters[i]);
            IGovernor(GOVERNOR).castVote(proposalIdHash, 1);
            vm.stopPrank();
        }

        vm.warp(block.timestamp + IGovernor(GOVERNOR).votingPeriod() + 1);
        vm.prank(CALLER);

        try IGovernor(GOVERNOR).queue(proposalIdHash) {
            // default path
        } catch {
            IGovernor(GOVERNOR).queue(targets, values, calldatas, descriptionHash);
        }

        vm.warp(block.timestamp + delay/2);

        IGovernor(GOVERNOR).execute(targets, values, calldatas, descriptionHash, proposer);
    }
}
