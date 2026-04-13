// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/GovernanceToken.sol";
import "../src/victim/SimpleDEX.sol";

/**
 * @title RunAll
 * @notice Runs all 4 phases of the admin-key-abuse scenario (~60 txs).
 */
contract RunAll is Script {
    GovernanceToken public govToken;
    SimpleDEX public dex;

    function run() external {
        _phase1_deploy();
        _phase2_normalActivity();
        _phase3_attack();
        _phase4_postAttack();
        console.log("All phases complete.");
    }

    function _phase1_deploy() internal {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);
        govToken = new GovernanceToken("GovToken", "GOV", 1_000_000e18);
        dex = new SimpleDEX(address(govToken));
        govToken.approve(address(dex), 500_000e18);
        dex.addLiquidity{value: 100 ether}(500_000e18);
        console.log("GovToken:", address(govToken));
        console.log("DEX:", address(dex));
        vm.stopBroadcast();
    }

    function _phase2_normalActivity() internal {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        uint256 user1Key = vm.envUint("USER1_KEY");
        uint256 user2Key = vm.envUint("USER2_KEY");
        uint256 user3Key = vm.envUint("USER3_KEY");
        uint256 user4Key = vm.envUint("USER4_KEY");
        uint256 user5Key = vm.envUint("USER5_KEY");

        address user1 = vm.addr(user1Key);
        address user2 = vm.addr(user2Key);
        address user3 = vm.addr(user3Key);
        address user4 = vm.addr(user4Key);
        address user5 = vm.addr(user5Key);
        address dexAddr = address(dex);

        // 20 mints
        vm.startBroadcast(deployerKey);
        govToken.mint(user1, 10_000e18);
        govToken.mint(user2, 8_000e18);
        govToken.mint(user3, 15_000e18);
        govToken.mint(user4, 5_000e18);
        govToken.mint(user5, 12_000e18);
        govToken.mint(user1, 3_000e18);
        govToken.mint(user2, 6_000e18);
        govToken.mint(user3, 4_000e18);
        govToken.mint(user4, 7_000e18);
        govToken.mint(user5, 9_000e18);
        govToken.mint(user1, 2_000e18);
        govToken.mint(user2, 11_000e18);
        govToken.mint(user3, 1_000e18);
        govToken.mint(user4, 8_000e18);
        govToken.mint(user5, 6_000e18);
        govToken.mint(user1, 4_000e18);
        govToken.mint(user2, 3_000e18);
        govToken.mint(user3, 7_000e18);
        govToken.mint(user4, 2_000e18);
        govToken.mint(user5, 5_000e18);
        vm.stopBroadcast();

        _phase2_transfers(user1Key, user2Key, user3Key, user4Key, user5Key);
        _phase2_approvals(user1Key, user2Key, user3Key, user4Key, user5Key, dexAddr);
        _phase2_swaps(user1Key, user2Key, user3Key, user4Key, user5Key);
    }

    function _phase2_transfers(
        uint256 u1, uint256 u2, uint256 u3, uint256 u4, uint256 u5
    ) internal {
        address a1 = vm.addr(u1);
        address a2 = vm.addr(u2);
        address a3 = vm.addr(u3);
        address a4 = vm.addr(u4);
        address a5 = vm.addr(u5);

        vm.startBroadcast(u1);
        govToken.transfer(a2, 1_000e18);
        govToken.transfer(a3, 500e18);
        govToken.transfer(a4, 2_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u2);
        govToken.transfer(a1, 800e18);
        govToken.transfer(a5, 1_500e18);
        govToken.transfer(a3, 600e18);
        vm.stopBroadcast();

        vm.startBroadcast(u3);
        govToken.transfer(a4, 1_200e18);
        govToken.transfer(a1, 900e18);
        govToken.transfer(a5, 400e18);
        vm.stopBroadcast();

        vm.startBroadcast(u4);
        govToken.transfer(a2, 700e18);
        govToken.transfer(a5, 1_000e18);
        govToken.transfer(a1, 300e18);
        vm.stopBroadcast();

        vm.startBroadcast(u5);
        govToken.transfer(a3, 2_000e18);
        govToken.transfer(a1, 1_100e18);
        govToken.transfer(a4, 500e18);
        vm.stopBroadcast();
    }

    function _phase2_approvals(
        uint256 u1, uint256 u2, uint256 u3, uint256 u4, uint256 u5,
        address dexAddr
    ) internal {
        address a1 = vm.addr(u1);
        address a2 = vm.addr(u2);
        address a3 = vm.addr(u3);
        address a4 = vm.addr(u4);
        address a5 = vm.addr(u5);

        vm.startBroadcast(u1);
        govToken.approve(dexAddr, 50_000e18);
        govToken.approve(a2, 5_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u2);
        govToken.approve(dexAddr, 50_000e18);
        govToken.approve(a3, 3_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u3);
        govToken.approve(dexAddr, 50_000e18);
        govToken.approve(a1, 2_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u4);
        govToken.approve(dexAddr, 50_000e18);
        govToken.approve(a5, 4_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u5);
        govToken.approve(dexAddr, 50_000e18);
        govToken.approve(a4, 1_000e18);
        vm.stopBroadcast();
    }

    function _phase2_swaps(
        uint256 u1, uint256 u2, uint256 u3, uint256 u4, uint256 u5
    ) internal {
        vm.startBroadcast(u1);
        dex.swapTokenForETH(500e18);
        vm.stopBroadcast();

        vm.startBroadcast(u2);
        dex.swapTokenForETH(300e18);
        vm.stopBroadcast();

        vm.startBroadcast(u3);
        dex.swapTokenForETH(200e18);
        vm.stopBroadcast();

        vm.startBroadcast(u4);
        dex.swapTokenForETH(400e18);
        vm.stopBroadcast();

        vm.startBroadcast(u5);
        dex.swapTokenForETH(100e18);
        vm.stopBroadcast();
    }

    function _phase3_attack() internal {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        address attackerAddr = vm.addr(attackerKey);
        address dexAddr = address(dex);

        // Ownership transfer (simulates key compromise)
        vm.startBroadcast(deployerKey);
        govToken.transferOwnership(attackerAddr);
        vm.stopBroadcast();

        // Attacker mints and dumps
        vm.startBroadcast(attackerKey);
        govToken.mint(attackerAddr, 10_000_000e18);
        govToken.approve(dexAddr, 10_000_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        console.log("Admin key abuse complete. ETH stolen.");
        vm.stopBroadcast();
    }

    function _phase4_postAttack() internal {
        uint256 user1Key = vm.envUint("USER1_KEY");
        uint256 user2Key = vm.envUint("USER2_KEY");
        uint256 user3Key = vm.envUint("USER3_KEY");
        address user3 = vm.addr(user3Key);
        address dexAddr = address(dex);

        vm.startBroadcast(user1Key);
        govToken.approve(dexAddr, 50_000e18);
        dex.swapTokenForETH(1_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        govToken.transfer(user3, 500e18);
        vm.stopBroadcast();

        vm.startBroadcast(user3Key);
        govToken.approve(dexAddr, 50_000e18);
        dex.swapTokenForETH(2_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user1Key);
        dex.swapTokenForETH(500e18);
        vm.stopBroadcast();
    }
}
