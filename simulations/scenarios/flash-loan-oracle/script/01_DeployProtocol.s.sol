// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";
import "../src/victim/MockUniswapPool.sol";
import "../src/victim/SimpleOracle.sol";
import "../src/victim/LendingPool.sol";

/**
 * @title DeployProtocol
 * @notice Phase 1: Deploy all protocol contracts (~5 txs).
 *         MockERC20 (USDC + WETH), SimplePriceOracle, LiquidityPool, LendingPool.
 *         Initialize with seed liquidity.
 */
contract DeployProtocol is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);

        // Deploy tokens
        MockERC20 tokenA = new MockERC20("Wrapped Ether", "WETH", 18);
        MockERC20 tokenB = new MockERC20("USD Coin", "USDC", 18);

        // Deploy AMM pool
        MockUniswapPool pool = new MockUniswapPool(address(tokenA), address(tokenB));

        // Mint and seed pool liquidity (1:1000 ratio — 1 WETH = 1000 USDC)
        tokenA.mint(msg.sender, 1_000_000e18);
        tokenB.mint(msg.sender, 1_000_000_000e18);
        tokenA.approve(address(pool), 500_000e18);
        tokenB.approve(address(pool), 500_000_000e18);
        pool.addLiquidity(500_000e18, 500_000_000e18);

        // Deploy oracle pointing to pool spot price
        SimpleOracle oracle = new SimpleOracle(address(pool));

        // Deploy lending pool
        LendingPool lending = new LendingPool(address(tokenA), address(tokenB), address(oracle));

        // Seed lending pool with borrowable USDC
        tokenB.mint(address(lending), 200_000_000e18);

        console.log("WETH:", address(tokenA));
        console.log("USDC:", address(tokenB));
        console.log("Pool:", address(pool));
        console.log("Oracle:", address(oracle));
        console.log("LendingPool:", address(lending));

        vm.stopBroadcast();
    }
}
