// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/VulnerableVault.sol";
import "../src/attacker/ReentrancyAttacker.sol";

/**
 * @title RunAll
 * @notice Runs all 4 phases of the reentrancy-drain scenario.
 *         ~60 total transactions: deploy(1) + normal(30) + attack(3) + dispersion(10).
 *
 *         For individual phase execution, use the numbered scripts.
 */
contract RunAll is Script {
    function run() external {
        // ==================== Phase 1: Deploy ====================
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);
        VulnerableVault vault = new VulnerableVault();
        console.log("VulnerableVault:", address(vault));
        vm.stopBroadcast();

        // ==================== Phase 2: Normal Activity (~30 txs) ====================
        uint256 user1Key = vm.envUint("USER1_KEY");
        uint256 user2Key = vm.envUint("USER2_KEY");
        uint256 user3Key = vm.envUint("USER3_KEY");
        uint256 user4Key = vm.envUint("USER4_KEY");
        uint256 user5Key = vm.envUint("USER5_KEY");

        // User 1: 3 deposits
        vm.startBroadcast(user1Key);
        vault.deposit{value: 5 ether}();
        vault.deposit{value: 2 ether}();
        vault.deposit{value: 1 ether}();
        vm.stopBroadcast();

        // User 2: 4 deposits
        vm.startBroadcast(user2Key);
        vault.deposit{value: 3 ether}();
        vault.deposit{value: 7 ether}();
        vault.deposit{value: 0.5 ether}();
        vault.deposit{value: 4 ether}();
        vm.stopBroadcast();

        // User 3: 5 deposits
        vm.startBroadcast(user3Key);
        vault.deposit{value: 10 ether}();
        vault.deposit{value: 2 ether}();
        vault.deposit{value: 8 ether}();
        vault.deposit{value: 1 ether}();
        vault.deposit{value: 3 ether}();
        vm.stopBroadcast();

        // User 4: 4 deposits
        vm.startBroadcast(user4Key);
        vault.deposit{value: 6 ether}();
        vault.deposit{value: 0.5 ether}();
        vault.deposit{value: 9 ether}();
        vault.deposit{value: 1 ether}();
        vm.stopBroadcast();

        // User 5: 4 deposits
        vm.startBroadcast(user5Key);
        vault.deposit{value: 4 ether}();
        vault.deposit{value: 2 ether}();
        vault.deposit{value: 7 ether}();
        vault.deposit{value: 3 ether}();
        vm.stopBroadcast();

        // 10 partial withdrawals
        vm.startBroadcast(user1Key);
        vault.withdraw(1 ether);
        vault.withdraw(2 ether);
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        vault.withdraw(1 ether);
        vault.withdraw(0.5 ether);
        vm.stopBroadcast();

        vm.startBroadcast(user3Key);
        vault.withdraw(3 ether);
        vault.withdraw(1 ether);
        vm.stopBroadcast();

        vm.startBroadcast(user4Key);
        vault.withdraw(2 ether);
        vault.withdraw(0.5 ether);
        vm.stopBroadcast();

        vm.startBroadcast(user5Key);
        vault.withdraw(1 ether);
        vault.withdraw(2 ether);
        vm.stopBroadcast();

        // ==================== Phase 3: Attack ====================
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");

        // Deploy + attack in same broadcast (same block on Anvil)
        vm.startBroadcast(attackerKey);
        ReentrancyAttacker attacker = new ReentrancyAttacker(address(vault));
        attacker.attack{value: 1 ether}();
        attacker.withdraw();
        vm.stopBroadcast();

        console.log("Attack complete. Vault drained.");

        // ==================== Phase 4: Fund Dispersion (~10 txs) ====================
        uint256 fresh1Key = vm.envUint("FRESH1_KEY");
        uint256 fresh2Key = vm.envUint("FRESH2_KEY");
        uint256 fresh3Key = vm.envUint("FRESH3_KEY");

        address fresh1 = vm.addr(fresh1Key);
        address fresh2 = vm.addr(fresh2Key);
        address fresh3 = vm.addr(fresh3Key);

        // Attacker disperses to fresh wallets
        vm.startBroadcast(attackerKey);
        payable(fresh1).transfer(10 ether);
        payable(fresh2).transfer(8 ether);
        payable(fresh3).transfer(5 ether);
        vm.stopBroadcast();

        // Cover traffic
        vm.startBroadcast(user1Key);
        vault.deposit{value: 1 ether}();
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        vault.deposit{value: 2 ether}();
        vm.stopBroadcast();

        // Multi-hop: fresh1 -> new address
        vm.startBroadcast(fresh1Key);
        payable(address(0xBEEF)).transfer(5 ether);
        vm.stopBroadcast();

        // More cover traffic
        vm.startBroadcast(user1Key);
        vault.deposit{value: 0.5 ether}();
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        vault.deposit{value: 0.5 ether}();
        vault.deposit{value: 1 ether}();
        vm.stopBroadcast();

        console.log("All phases complete.");
    }
}
