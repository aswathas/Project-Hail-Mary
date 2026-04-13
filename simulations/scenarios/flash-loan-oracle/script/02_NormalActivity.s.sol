// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";

interface IPoolActivity {
    function addLiquidity(uint256 amountA, uint256 amountB) external;
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
}

interface ILendingActivity {
    function depositCollateral(uint256 amount) external;
    function borrow(uint256 amount) external;
    function repay(uint256 amount) external;
}

/**
 * @title NormalActivity
 * @notice Phase 2: ~45 normal user transactions.
 *         15 add-liquidity, 10 collateral+borrow, 10 swaps, 5 repayments, 5 extra.
 */
contract NormalActivity is Script {
    function run() external {
        address tokenAAddr = vm.envAddress("TOKEN_A");
        address tokenBAddr = vm.envAddress("TOKEN_B");
        address poolAddr = vm.envAddress("POOL_ADDRESS");
        address lendingAddr = vm.envAddress("LENDING_ADDRESS");

        MockERC20 tokenA = MockERC20(tokenAAddr);
        MockERC20 tokenB = MockERC20(tokenBAddr);
        IPoolActivity pool = IPoolActivity(poolAddr);
        ILendingActivity lending = ILendingActivity(lendingAddr);

        uint256 user1Key = vm.envUint("USER1_KEY");
        uint256 user2Key = vm.envUint("USER2_KEY");
        uint256 user3Key = vm.envUint("USER3_KEY");
        uint256 user4Key = vm.envUint("USER4_KEY");
        uint256 user5Key = vm.envUint("USER5_KEY");

        // --- 15 add-liquidity transactions (3 per user) ---

        // User 1: add liquidity
        vm.startBroadcast(user1Key);
        tokenA.mint(msg.sender, 10_000e18);
        tokenB.mint(msg.sender, 10_000_000e18);
        tokenA.approve(poolAddr, 10_000e18);
        tokenB.approve(poolAddr, 10_000_000e18);
        pool.addLiquidity(1_000e18, 1_000_000e18);
        pool.addLiquidity(500e18, 500_000e18);
        pool.addLiquidity(200e18, 200_000e18);
        vm.stopBroadcast();

        // User 2: add liquidity
        vm.startBroadcast(user2Key);
        tokenA.mint(msg.sender, 10_000e18);
        tokenB.mint(msg.sender, 10_000_000e18);
        tokenA.approve(poolAddr, 10_000e18);
        tokenB.approve(poolAddr, 10_000_000e18);
        pool.addLiquidity(800e18, 800_000e18);
        pool.addLiquidity(300e18, 300_000e18);
        pool.addLiquidity(600e18, 600_000e18);
        vm.stopBroadcast();

        // User 3: add liquidity
        vm.startBroadcast(user3Key);
        tokenA.mint(msg.sender, 10_000e18);
        tokenB.mint(msg.sender, 10_000_000e18);
        tokenA.approve(poolAddr, 10_000e18);
        tokenB.approve(poolAddr, 10_000_000e18);
        pool.addLiquidity(1_500e18, 1_500_000e18);
        pool.addLiquidity(400e18, 400_000e18);
        pool.addLiquidity(100e18, 100_000e18);
        vm.stopBroadcast();

        // User 4: add liquidity
        vm.startBroadcast(user4Key);
        tokenA.mint(msg.sender, 10_000e18);
        tokenB.mint(msg.sender, 10_000_000e18);
        tokenA.approve(poolAddr, 10_000e18);
        tokenB.approve(poolAddr, 10_000_000e18);
        pool.addLiquidity(700e18, 700_000e18);
        pool.addLiquidity(250e18, 250_000e18);
        pool.addLiquidity(350e18, 350_000e18);
        vm.stopBroadcast();

        // User 5: add liquidity
        vm.startBroadcast(user5Key);
        tokenA.mint(msg.sender, 10_000e18);
        tokenB.mint(msg.sender, 10_000_000e18);
        tokenA.approve(poolAddr, 10_000e18);
        tokenB.approve(poolAddr, 10_000_000e18);
        pool.addLiquidity(900e18, 900_000e18);
        pool.addLiquidity(450e18, 450_000e18);
        pool.addLiquidity(550e18, 550_000e18);
        vm.stopBroadcast();

        // --- 10 collateral deposits + borrows (2 per user) ---

        vm.startBroadcast(user1Key);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(500e18);
        lending.borrow(200_000e18);
        lending.depositCollateral(300e18);
        lending.borrow(100_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(400e18);
        lending.borrow(150_000e18);
        lending.depositCollateral(200e18);
        lending.borrow(80_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user3Key);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(600e18);
        lending.borrow(250_000e18);
        lending.depositCollateral(100e18);
        lending.borrow(40_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user4Key);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(350e18);
        lending.borrow(140_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user5Key);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(450e18);
        lending.borrow(180_000e18);
        lending.depositCollateral(250e18);
        lending.borrow(100_000e18);
        vm.stopBroadcast();

        // --- 10 normal swaps ---

        vm.startBroadcast(user1Key);
        pool.swap(tokenAAddr, 50e18);
        pool.swap(tokenAAddr, 30e18);
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        pool.swap(tokenAAddr, 80e18);
        pool.swap(tokenAAddr, 20e18);
        vm.stopBroadcast();

        vm.startBroadcast(user3Key);
        pool.swap(tokenAAddr, 40e18);
        pool.swap(tokenAAddr, 60e18);
        vm.stopBroadcast();

        vm.startBroadcast(user4Key);
        pool.swap(tokenAAddr, 25e18);
        pool.swap(tokenAAddr, 35e18);
        vm.stopBroadcast();

        vm.startBroadcast(user5Key);
        pool.swap(tokenAAddr, 45e18);
        pool.swap(tokenAAddr, 55e18);
        vm.stopBroadcast();

        // --- 5 partial repayments ---

        vm.startBroadcast(user1Key);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(50_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user2Key);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(30_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user3Key);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(40_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user4Key);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(20_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(user5Key);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(25_000e18);
        vm.stopBroadcast();

        console.log("Normal activity complete: ~45 transactions");
    }
}
