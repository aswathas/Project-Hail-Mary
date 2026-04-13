// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";

interface IGovPost {
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

interface IDEXPost {
    function swapTokenForETH(uint256 tokenAmount) external returns (uint256);
}

/**
 * @title PostAttack
 * @notice Phase 4: ~7 post-attack transactions.
 *         Users try to interact with the now-worthless token.
 *         Some swaps return near-zero ETH. Shows the devastation.
 */
contract PostAttack is Script {
    function run() external {
        address govAddr = vm.envAddress("GOV_ADDRESS");
        address dexAddr = vm.envAddress("DEX_ADDRESS");

        IGovPost gov = IGovPost(govAddr);

        uint256 user1Key = vm.envUint("USER1_KEY");
        uint256 user2Key = vm.envUint("USER2_KEY");
        uint256 user3Key = vm.envUint("USER3_KEY");

        // User 1: tries to swap tokens — gets almost nothing
        vm.startBroadcast(user1Key);
        gov.approve(dexAddr, 50_000e18);
        IDEXPost(dexAddr).swapTokenForETH(1_000e18);
        vm.stopBroadcast();

        // User 2: tries to transfer tokens to user 3
        vm.startBroadcast(user2Key);
        address user3 = vm.addr(user3Key);
        gov.transfer(user3, 500e18);
        vm.stopBroadcast();

        // User 3: tries another swap
        vm.startBroadcast(user3Key);
        gov.approve(dexAddr, 50_000e18);
        IDEXPost(dexAddr).swapTokenForETH(2_000e18);
        vm.stopBroadcast();

        // User 1: one more swap attempt
        vm.startBroadcast(user1Key);
        IDEXPost(dexAddr).swapTokenForETH(500e18);
        vm.stopBroadcast();

        console.log("Post-attack activity complete. Token value has collapsed.");
    }
}
