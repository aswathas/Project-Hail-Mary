// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

/**
 * @title SimpleDEX
 * @notice Simple constant-product AMM (x * y = k). Victims submit swaps here.
 *         MEV bot front-runs and back-runs in the same block to extract value.
 *         No slippage protection — this is intentionally vulnerable.
 */
contract SimpleDEX {
    MockERC20 public tokenA;
    MockERC20 public tokenB;
    uint256 public reserveA;
    uint256 public reserveB;

    event Swap(address indexed trader, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event AddLiquidity(address indexed provider, uint256 amountA, uint256 amountB);
    event RemoveLiquidity(address indexed provider, uint256 amountA, uint256 amountB);

    constructor(address _tokenA, address _tokenB) {
        tokenA = MockERC20(_tokenA);
        tokenB = MockERC20(_tokenB);
    }

    function addLiquidity(uint256 amountA, uint256 amountB) external {
        tokenA.transferFrom(msg.sender, address(this), amountA);
        tokenB.transferFrom(msg.sender, address(this), amountB);
        reserveA += amountA;
        reserveB += amountB;
        emit AddLiquidity(msg.sender, amountA, amountB);
    }

    function removeLiquidity(uint256 amountA, uint256 amountB) external {
        require(amountA <= reserveA, "Insufficient reserveA");
        require(amountB <= reserveB, "Insufficient reserveB");
        reserveA -= amountA;
        reserveB -= amountB;
        tokenA.transfer(msg.sender, amountA);
        tokenB.transfer(msg.sender, amountB);
        emit RemoveLiquidity(msg.sender, amountA, amountB);
    }

    function swap(address tokenIn, uint256 amountIn) external returns (uint256 amountOut) {
        require(amountIn > 0, "Zero amount");

        if (tokenIn == address(tokenA)) {
            // Swap tokenA -> tokenB using constant product formula
            amountOut = (amountIn * reserveB) / (reserveA + amountIn);
            require(amountOut > 0, "Insufficient output");
            tokenA.transferFrom(msg.sender, address(this), amountIn);
            tokenB.transfer(msg.sender, amountOut);
            reserveA += amountIn;
            reserveB -= amountOut;
            emit Swap(msg.sender, address(tokenA), address(tokenB), amountIn, amountOut);
        } else if (tokenIn == address(tokenB)) {
            // Swap tokenB -> tokenA using constant product formula
            amountOut = (amountIn * reserveA) / (reserveB + amountIn);
            require(amountOut > 0, "Insufficient output");
            tokenB.transferFrom(msg.sender, address(this), amountIn);
            tokenA.transfer(msg.sender, amountOut);
            reserveB += amountIn;
            reserveA -= amountOut;
            emit Swap(msg.sender, address(tokenB), address(tokenA), amountIn, amountOut);
        } else {
            revert("Invalid token");
        }
    }

    function getAmountOut(address tokenIn, uint256 amountIn) external view returns (uint256) {
        if (tokenIn == address(tokenA)) {
            return (amountIn * reserveB) / (reserveA + amountIn);
        } else {
            return (amountIn * reserveA) / (reserveB + amountIn);
        }
    }

    function getReserves() external view returns (uint256, uint256) {
        return (reserveA, reserveB);
    }
}
