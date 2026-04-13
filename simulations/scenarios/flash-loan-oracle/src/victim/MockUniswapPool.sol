// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

/**
 * @title MockUniswapPool
 * @notice Simplified AMM pool with flash loan capability.
 *         Spot price is reserve ratio -- manipulable via large swaps.
 */
contract MockUniswapPool {
    MockERC20 public tokenA;
    MockERC20 public tokenB;
    uint256 public reserveA;
    uint256 public reserveB;

    event Swap(address indexed trader, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event FlashLoan(address indexed borrower, address token, uint256 amount);
    event AddLiquidity(address indexed provider, uint256 amountA, uint256 amountB);

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

    function swap(address tokenIn, uint256 amountIn) external returns (uint256 amountOut) {
        if (tokenIn == address(tokenA)) {
            amountOut = (amountIn * reserveB) / (reserveA + amountIn);
            tokenA.transferFrom(msg.sender, address(this), amountIn);
            tokenB.transfer(msg.sender, amountOut);
            reserveA += amountIn;
            reserveB -= amountOut;
            emit Swap(msg.sender, address(tokenA), address(tokenB), amountIn, amountOut);
        } else {
            amountOut = (amountIn * reserveA) / (reserveB + amountIn);
            tokenB.transferFrom(msg.sender, address(this), amountIn);
            tokenA.transfer(msg.sender, amountOut);
            reserveB += amountIn;
            reserveA -= amountOut;
            emit Swap(msg.sender, address(tokenB), address(tokenA), amountIn, amountOut);
        }
    }

    function flashLoan(address token, uint256 amount, bytes calldata data) external {
        uint256 balanceBefore;
        if (token == address(tokenA)) {
            balanceBefore = tokenA.balanceOf(address(this));
            tokenA.transfer(msg.sender, amount);
        } else {
            balanceBefore = tokenB.balanceOf(address(this));
            tokenB.transfer(msg.sender, amount);
        }

        emit FlashLoan(msg.sender, token, amount);

        (bool success,) = msg.sender.call(data);
        require(success, "Flash loan callback failed");

        if (token == address(tokenA)) {
            require(tokenA.balanceOf(address(this)) >= balanceBefore, "Flash loan not repaid");
        } else {
            require(tokenB.balanceOf(address(this)) >= balanceBefore, "Flash loan not repaid");
        }
    }

    function getSpotPrice() external view returns (uint256) {
        if (reserveA == 0) return 0;
        return (reserveB * 1e18) / reserveA;
    }
}
