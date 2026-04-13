// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";

interface IGovToken {
    function mint(address to, uint256 amount) external;
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

interface IDEX {
    function swapTokenForETH(uint256 tokenAmount) external returns (uint256);
}

/**
 * @title NormalActivity
 * @notice Phase 2: ~35 normal transactions.
 *         20 mints to users, 15 user-to-user transfers,
 *         10 approvals, 5 small DEX swaps.
 */
contract NormalActivity is Script {
    function run() external {
        address govAddr = vm.envAddress("GOV_ADDRESS");
        address dexAddr = vm.envAddress("DEX_ADDRESS");

        IGovToken gov = IGovToken(govAddr);

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

        // --- 20 mints from owner (deployer) to various users ---
        vm.startBroadcast(deployerKey);
        gov.mint(user1, 10_000e18);
        gov.mint(user2, 8_000e18);
        gov.mint(user3, 15_000e18);
        gov.mint(user4, 5_000e18);
        gov.mint(user5, 12_000e18);
        gov.mint(user1, 3_000e18);
        gov.mint(user2, 6_000e18);
        gov.mint(user3, 4_000e18);
        gov.mint(user4, 7_000e18);
        gov.mint(user5, 9_000e18);
        gov.mint(user1, 2_000e18);
        gov.mint(user2, 11_000e18);
        gov.mint(user3, 1_000e18);
        gov.mint(user4, 8_000e18);
        gov.mint(user5, 6_000e18);
        gov.mint(user1, 4_000e18);
        gov.mint(user2, 3_000e18);
        gov.mint(user3, 7_000e18);
        gov.mint(user4, 2_000e18);
        gov.mint(user5, 5_000e18);
        vm.stopBroadcast();

        // --- 15 user-to-user transfers ---
        vm.startBroadcast(user1Key);
        gov.transfer(user2, 1_000e18);
        gov.transfer(user3, 500e18);
        gov.transfer(user4, 2_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        gov.transfer(user1, 800e18);
        gov.transfer(user5, 1_500e18);
        gov.transfer(user3, 600e18);
        vm.stopBroadcast();

        vm.startBroadcast(user3Key);
        gov.transfer(user4, 1_200e18);
        gov.transfer(user1, 900e18);
        gov.transfer(user5, 400e18);
        vm.stopBroadcast();

        vm.startBroadcast(user4Key);
        gov.transfer(user2, 700e18);
        gov.transfer(user5, 1_000e18);
        gov.transfer(user1, 300e18);
        vm.stopBroadcast();

        vm.startBroadcast(user5Key);
        gov.transfer(user3, 2_000e18);
        gov.transfer(user1, 1_100e18);
        gov.transfer(user4, 500e18);
        vm.stopBroadcast();

        // --- 10 approvals (users approve DEX for swapping) ---
        vm.startBroadcast(user1Key);
        gov.approve(dexAddr, 50_000e18);
        gov.approve(user2, 5_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        gov.approve(dexAddr, 50_000e18);
        gov.approve(user3, 3_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user3Key);
        gov.approve(dexAddr, 50_000e18);
        gov.approve(user1, 2_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user4Key);
        gov.approve(dexAddr, 50_000e18);
        gov.approve(user5, 4_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user5Key);
        gov.approve(dexAddr, 50_000e18);
        gov.approve(user4, 1_000e18);
        vm.stopBroadcast();

        // --- 5 small DEX swaps ---
        vm.startBroadcast(user1Key);
        IDEX(dexAddr).swapTokenForETH(500e18);
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        IDEX(dexAddr).swapTokenForETH(300e18);
        vm.stopBroadcast();

        vm.startBroadcast(user3Key);
        IDEX(dexAddr).swapTokenForETH(200e18);
        vm.stopBroadcast();

        vm.startBroadcast(user4Key);
        IDEX(dexAddr).swapTokenForETH(400e18);
        vm.stopBroadcast();

        vm.startBroadcast(user5Key);
        IDEX(dexAddr).swapTokenForETH(100e18);
        vm.stopBroadcast();

        console.log("Normal activity complete: ~50 txs (20 mints, 15 transfers, 10 approvals, 5 swaps)");
    }
}
