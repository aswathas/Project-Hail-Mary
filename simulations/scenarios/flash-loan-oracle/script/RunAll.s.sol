// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";
import "../src/victim/MockUniswapPool.sol";
import "../src/victim/SimpleOracle.sol";
import "../src/victim/LendingPool.sol";
import "../src/attacker/FlashLoanAttacker.sol";

contract RunAll is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");

        vm.startBroadcast(deployerKey);

        // Deploy tokens
        MockERC20 tokenA = new MockERC20("Token A", "TKA", 18);
        MockERC20 tokenB = new MockERC20("Token B", "TKB", 18);

        // Deploy pool and seed liquidity
        MockUniswapPool pool = new MockUniswapPool(address(tokenA), address(tokenB));
        tokenA.mint(msg.sender, 1_000_000e18);
        tokenB.mint(msg.sender, 1_000_000e18);
        tokenA.approve(address(pool), 500_000e18);
        tokenB.approve(address(pool), 500_000e18);
        pool.addLiquidity(500_000e18, 500_000e18);

        // Deploy oracle and lending
        SimpleOracle oracle = new SimpleOracle(address(pool));
        LendingPool lending = new LendingPool(address(tokenA), address(tokenB), address(oracle));
        tokenB.mint(address(lending), 100_000e18); // seed lending pool

        console.log("Pool:", address(pool));
        console.log("Oracle:", address(oracle));
        console.log("Lending:", address(lending));

        vm.stopBroadcast();

        // Normal activity
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        tokenA.mint(msg.sender, 10_000e18);
        tokenA.approve(address(pool), 1_000e18);
        pool.swap(address(tokenA), 1_000e18);
        vm.stopBroadcast();

        // Attack
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        vm.startBroadcast(attackerKey);
        FlashLoanAttacker attacker = new FlashLoanAttacker(
            address(pool), address(lending), address(tokenA), address(tokenB)
        );
        attacker.attack(400_000e18);
        console.log("Flash loan oracle attack executed");
        vm.stopBroadcast();
    }
}
