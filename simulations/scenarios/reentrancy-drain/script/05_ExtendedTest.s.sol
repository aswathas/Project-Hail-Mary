// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/VulnerableVault.sol";
import "../src/attacker/ReentrancyAttacker.sol";

/**
 * @title ExtendedTest
 * @notice Extended simulation with 200+ transactions and TWO reentrancy attacks
 *         to fully test signal and pattern detection.
 *
 *         Phases:
 *         1. Deploy vault
 *         2. Generate ~100 normal transactions (deposits, withdrawals)
 *         3. First reentrancy attack (single drain)
 *         4. Generate ~50 cover transactions
 *         5. Second reentrancy attack (different attacker, same vault)
 *         6. Final dispersal and cover traffic (~50 more)
 */
contract ExtendedTest is Script {
    VulnerableVault vault;
    uint256 user1Key;
    uint256 user2Key;
    uint256 user3Key;
    uint256 user4Key;
    uint256 user5Key;
    uint256 fresh1Key;
    uint256 fresh2Key;
    uint256 fresh3Key;
    uint256 attacker1Key;
    uint256 attacker2Key;

    function run() external {
        // ==================== Phase 1: Deploy ====================
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);
        vault = new VulnerableVault();
        console.log("VulnerableVault deployed:", address(vault));
        vm.stopBroadcast();

        // ==================== Phase 2: Heavy Normal Activity (~100 txs) ====================
        console.log("Phase 2: Generating ~100 normal transactions...");

        // Get all user keys
        user1Key = vm.envUint("USER1_KEY");
        user2Key = vm.envUint("USER2_KEY");
        user3Key = vm.envUint("USER3_KEY");
        user4Key = vm.envUint("USER4_KEY");
        user5Key = vm.envUint("USER5_KEY");
        fresh1Key = vm.envUint("FRESH1_KEY");
        fresh2Key = vm.envUint("FRESH2_KEY");
        fresh3Key = vm.envUint("FRESH3_KEY");

        uint256[] memory userKeys = new uint256[](8);
        userKeys[0] = user1Key;
        userKeys[1] = user2Key;
        userKeys[2] = user3Key;
        userKeys[3] = user4Key;
        userKeys[4] = user5Key;
        userKeys[5] = fresh1Key;
        userKeys[6] = fresh2Key;
        userKeys[7] = fresh3Key;

        // Each user: 5 deposits + 3 withdrawals = 8 txs per user
        // 8 users = 64 txs
        for (uint256 i = 0; i < 8; i++) {
            vm.startBroadcast(userKeys[i]);

            // 5 deposits of varying amounts
            vault.deposit{value: 1 ether}();
            vault.deposit{value: 2 ether}();
            vault.deposit{value: 3 ether}();
            vault.deposit{value: 0.5 ether}();
            vault.deposit{value: 1.5 ether}();

            // 3 withdrawals
            vault.withdraw(1 ether);
            vault.withdraw(2 ether);
            vault.withdraw(0.5 ether);

            vm.stopBroadcast();
        }

        // Additional transactions to reach ~100
        // 5 more cycles of 4 txs each = 20 more txs
        for (uint256 cycle = 0; cycle < 5; cycle++) {
            uint256 idx = cycle % 8;
            vm.startBroadcast(userKeys[idx]);
            vault.deposit{value: 0.25 ether}();
            vault.deposit{value: 0.75 ether}();
            vault.withdraw(0.5 ether);
            vault.withdraw(0.25 ether);
            vm.stopBroadcast();
        }

        console.log("Normal activity complete (~100 txs)");

        // ==================== Phase 3: First Reentrancy Attack ====================
        console.log("Phase 3: Executing FIRST reentrancy attack...");
        attacker1Key = vm.envUint("ATTACKER_KEY");

        vm.startBroadcast(attacker1Key);
        ReentrancyAttacker attacker1 = new ReentrancyAttacker(address(vault));
        attacker1.attack{value: 1 ether}();
        attacker1.withdraw();
        vm.stopBroadcast();

        console.log("First attack complete");

        // ==================== Phase 4: Cover Traffic (~50 txs) ====================
        console.log("Phase 4: Generating cover traffic...");
        for (uint256 i = 0; i < 8; i++) {
            vm.startBroadcast(userKeys[i]);
            vault.deposit{value: 0.1 ether}();
            vault.withdraw(0.05 ether);
            vault.deposit{value: 0.2 ether}();
            vault.withdraw(0.1 ether);
            vault.deposit{value: 0.15 ether}();
            vm.stopBroadcast();
        }
        console.log("Cover traffic complete (~50 txs)");

        // ==================== Phase 5: Second Reentrancy Attack ====================
        console.log("Phase 5: Executing SECOND reentrancy attack...");
        attacker2Key = fresh3Key;

        vm.startBroadcast(attacker2Key);
        ReentrancyAttacker attacker2 = new ReentrancyAttacker(address(vault));
        attacker2.attack{value: 0.5 ether}();
        attacker2.withdraw();
        vm.stopBroadcast();

        console.log("Second attack complete");

        // ==================== Phase 6: Final Dispersal (~30 txs) ====================
        console.log("Phase 6: Final fund dispersal...");

        // Attackers disperse funds
        vm.startBroadcast(attacker1Key);
        payable(vm.addr(fresh1Key)).transfer(5 ether);
        payable(vm.addr(fresh2Key)).transfer(4 ether);
        payable(vm.addr(fresh3Key)).transfer(3 ether);
        vm.stopBroadcast();

        vm.startBroadcast(attacker2Key);
        payable(vm.addr(fresh1Key)).transfer(2 ether);
        payable(vm.addr(fresh2Key)).transfer(1 ether);
        vm.stopBroadcast();

        // Final cover traffic
        for (uint256 i = 0; i < 5; i++) {
            vm.startBroadcast(userKeys[i]);
            vault.deposit{value: 0.05 ether}();
            vault.withdraw(0.02 ether);
            vm.stopBroadcast();
        }

        console.log("Extended test complete. Total ~150+ transactions generated.");
    }
}
