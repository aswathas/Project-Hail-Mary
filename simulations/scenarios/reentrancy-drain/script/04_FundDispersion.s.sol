// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";

interface IVaultDispersion {
    function deposit() external payable;
}

/**
 * @title FundDispersion
 * @notice Phase 4: ~10 post-attack transactions.
 *         Attacker disperses stolen funds to fresh wallets (tests fund_dispersion_post_attack).
 *         One fresh wallet forwards to another (tests multi_hop_fund_trail).
 *         Cover traffic: normal user interactions between attack blocks.
 */
contract FundDispersion is Script {
    function run() external {
        address vaultAddr = vm.envAddress("VAULT_ADDRESS");
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        uint256 user1Key = vm.envUint("USER1_KEY");
        uint256 user2Key = vm.envUint("USER2_KEY");

        // Fresh wallet keys — use env vars for deterministic Anvil keys
        uint256 fresh1Key = vm.envUint("FRESH1_KEY");
        uint256 fresh2Key = vm.envUint("FRESH2_KEY");
        uint256 fresh3Key = vm.envUint("FRESH3_KEY");

        address fresh1 = vm.addr(fresh1Key);
        address fresh2 = vm.addr(fresh2Key);
        address fresh3 = vm.addr(fresh3Key);

        // --- Attacker disperses stolen ETH to 3 fresh wallets ---
        vm.startBroadcast(attackerKey);
        payable(fresh1).transfer(10 ether);
        payable(fresh2).transfer(8 ether);
        payable(fresh3).transfer(5 ether);
        vm.stopBroadcast();

        // --- Cover traffic: normal users still interacting ---
        vm.startBroadcast(user1Key);
        IVaultDispersion(vaultAddr).deposit{value: 1 ether}();
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        IVaultDispersion(vaultAddr).deposit{value: 2 ether}();
        vm.stopBroadcast();

        // --- Multi-hop: fresh1 forwards to a new address (tests multi_hop_fund_trail) ---
        // fresh1 received 10 ETH from attacker, now sends 5 to fresh2's address
        // This creates a 2-hop trail: attacker -> fresh1 -> (new destination)
        vm.startBroadcast(fresh1Key);
        payable(address(0xBEEF)).transfer(5 ether);
        vm.stopBroadcast();

        // --- More cover traffic ---
        vm.startBroadcast(user1Key);
        IVaultDispersion(vaultAddr).deposit{value: 0.5 ether}();
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        IVaultDispersion(vaultAddr).deposit{value: 0.5 ether}();
        IVaultDispersion(vaultAddr).deposit{value: 1 ether}();
        vm.stopBroadcast();

        console.log("Fund dispersion + cover traffic complete");
    }
}
