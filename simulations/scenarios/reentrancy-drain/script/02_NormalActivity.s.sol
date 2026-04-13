// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";

interface IVaultScript {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
}

/**
 * @title NormalActivity
 * @notice Phase 2: ~30 normal user transactions on VulnerableVault.
 *         20 deposits from different users + 10 partial withdrawals.
 */
contract NormalActivity is Script {
    function run() external {
        address vaultAddr = vm.envAddress("VAULT_ADDRESS");
        IVaultScript vault = IVaultScript(vaultAddr);

        // Anvil default private keys (accounts 1-5 as normal users)
        uint256 user1Key = vm.envUint("USER1_KEY");
        uint256 user2Key = vm.envUint("USER2_KEY");
        uint256 user3Key = vm.envUint("USER3_KEY");
        uint256 user4Key = vm.envUint("USER4_KEY");
        uint256 user5Key = vm.envUint("USER5_KEY");

        // --- 20 deposits from varied users with varied amounts ---

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

        // --- 10 partial withdrawals ---

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

        console.log("Normal activity complete: 20 deposits + 10 withdrawals");
    }
}
