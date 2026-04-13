// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";

interface IVaultScript {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
}

contract NormalActivity is Script {
    function run() external {
        address vaultAddr = vm.envAddress("VAULT_ADDRESS");
        IVaultScript vault = IVaultScript(vaultAddr);

        // User 1: deposits 5 ETH
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        vault.deposit{value: 5 ether}();
        vm.stopBroadcast();

        // User 2: deposits 3 ETH
        uint256 user2Key = vm.envUint("USER2_KEY");
        vm.startBroadcast(user2Key);
        vault.deposit{value: 3 ether}();
        vm.stopBroadcast();

        // User 3: deposits 10 ETH
        uint256 user3Key = vm.envUint("USER3_KEY");
        vm.startBroadcast(user3Key);
        vault.deposit{value: 10 ether}();
        vm.stopBroadcast();

        // User 1: small withdraw of 1 ETH
        vm.startBroadcast(user1Key);
        vault.withdraw(1 ether);
        vm.stopBroadcast();

        // User 2: another deposit
        vm.startBroadcast(user2Key);
        vault.deposit{value: 2 ether}();
        vm.stopBroadcast();

        console.log("Normal activity complete. Vault should have ~19 ETH");
    }
}
