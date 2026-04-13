// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

interface IDEXActivity {
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
}

/**
 * @title NormalUsers
 * @notice Simulates normal trading activity on SimpleDEX.
 *         Multiple users perform legitimate swaps to create realistic
 *         background noise that ChainSentinel must filter through.
 */
contract NormalUsers {
    IDEXActivity public dex;

    constructor(address _dex) {
        dex = IDEXActivity(_dex);
    }

    /// @notice Execute a normal swap on the DEX
    function normalSwap(address tokenIn, uint256 amountIn) external returns (uint256) {
        MockERC20(tokenIn).approve(address(dex), amountIn);
        return dex.swap(tokenIn, amountIn);
    }

    /// @notice Execute multiple small swaps to simulate active trading
    function multiSwap(address tokenIn, uint256 totalAmount, uint256 splits) external {
        uint256 perSwap = totalAmount / splits;
        MockERC20(tokenIn).approve(address(dex), totalAmount);
        for (uint256 i = 0; i < splits; i++) {
            dex.swap(tokenIn, perSwap);
        }
    }
}
