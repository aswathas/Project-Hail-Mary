// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/GovernanceToken.sol";
import "../src/victim/SimpleDEX.sol";

contract RunAll is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");

        // Phase 1: Deploy protocol
        vm.startBroadcast(deployerKey);
        GovernanceToken govToken = new GovernanceToken("GovToken", "GOV", 1_000_000e18);
        SimpleDEX dex = new SimpleDEX(address(govToken));

        // Seed DEX liquidity
        govToken.approve(address(dex), 500_000e18);
        dex.addLiquidity{value: 100 ether}(500_000e18);

        console.log("GovToken:", address(govToken));
        console.log("DEX:", address(dex));
        vm.stopBroadcast();

        // Phase 2: Normal activity
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        // User buys some tokens from DEX (small swap)
        vm.stopBroadcast();

        // Phase 3: Attack -- compromise admin key, transfer ownership, mint, dump
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");

        // Attacker gets deployer to transfer ownership (simulates key compromise)
        vm.startBroadcast(deployerKey);
        govToken.transferOwnership(vm.addr(attackerKey));
        vm.stopBroadcast();

        // Attacker mints massive supply and dumps
        vm.startBroadcast(attackerKey);
        govToken.mint(vm.addr(attackerKey), 10_000_000e18);
        govToken.approve(address(dex), 10_000_000e18);
        dex.swapTokenForETH(5_000_000e18);
        console.log("Admin key abuse complete. ETH stolen.");
        vm.stopBroadcast();
    }
}
