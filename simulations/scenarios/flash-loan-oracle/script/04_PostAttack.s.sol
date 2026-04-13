// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";

interface IPoolPost {
    function addLiquidity(uint256 amountA, uint256 amountB) external;
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
}

interface ILendingPost {
    function depositCollateral(uint256 amount) external;
    function borrow(uint256 amount) external;
    function repay(uint256 amount) external;
}

/**
 * @title PostAttack
 * @notice Phase 4: ~10 post-attack transactions.
 *         Normal users continue activity, some operations may fail
 *         due to drained pool. Shows contrast between pre and post attack.
 */
contract PostAttack is Script {
    function run() external {
        address tokenAAddr = vm.envAddress("TOKEN_A");
        address tokenBAddr = vm.envAddress("TOKEN_B");
        address poolAddr = vm.envAddress("POOL_ADDRESS");
        address lendingAddr = vm.envAddress("LENDING_ADDRESS");

        MockERC20 tokenA = MockERC20(tokenAAddr);
        MockERC20 tokenB = MockERC20(tokenBAddr);

        uint256 user1Key = vm.envUint("USER1_KEY");
        uint256 user2Key = vm.envUint("USER2_KEY");
        uint256 user3Key = vm.envUint("USER3_KEY");

        // User 1: tries normal swap (smaller amount — may still succeed)
        vm.startBroadcast(user1Key);
        tokenA.mint(msg.sender, 1_000e18);
        tokenA.approve(poolAddr, 1_000e18);
        IPoolPost(poolAddr).swap(tokenAAddr, 10e18);
        IPoolPost(poolAddr).swap(tokenAAddr, 5e18);
        vm.stopBroadcast();

        // User 2: tries to repay existing debt
        vm.startBroadcast(user2Key);
        tokenB.mint(msg.sender, 100_000e18);
        tokenB.approve(lendingAddr, 100_000e18);
        ILendingPost(lendingAddr).repay(30_000e18);
        ILendingPost(lendingAddr).repay(20_000e18);
        vm.stopBroadcast();

        // User 3: small swap
        vm.startBroadcast(user3Key);
        tokenA.mint(msg.sender, 500e18);
        tokenA.approve(poolAddr, 500e18);
        IPoolPost(poolAddr).swap(tokenAAddr, 5e18);
        vm.stopBroadcast();

        // User 1: tries to add small liquidity
        vm.startBroadcast(user1Key);
        tokenB.mint(msg.sender, 500_000e18);
        tokenB.approve(poolAddr, 500_000e18);
        IPoolPost(poolAddr).addLiquidity(100e18, 100_000e18);
        vm.stopBroadcast();

        // User 3: another small swap
        vm.startBroadcast(user3Key);
        IPoolPost(poolAddr).swap(tokenAAddr, 3e18);
        vm.stopBroadcast();

        console.log("Post-attack activity complete");
    }
}
