// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./MockERC20.sol";

interface IDEX {
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
}

contract SandwichAttacker {
    address public owner;
    IDEX public dex;

    event FrontRun(address tokenIn, uint256 amountIn, uint256 amountOut);
    event BackRun(address tokenIn, uint256 amountIn, uint256 amountOut);

    constructor(address _dex) {
        owner = msg.sender;
        dex = IDEX(_dex);
    }

    function frontrun(address tokenIn, uint256 amount) external returns (uint256 out) {
        require(msg.sender == owner);
        MockERC20(tokenIn).approve(address(dex), amount);
        out = dex.swap(tokenIn, amount);
        emit FrontRun(tokenIn, amount, out);
    }

    function backrun(address tokenIn, uint256 amount) external returns (uint256 out) {
        require(msg.sender == owner);
        MockERC20(tokenIn).approve(address(dex), amount);
        out = dex.swap(tokenIn, amount);
        emit BackRun(tokenIn, amount, out);
    }

    function drain(address token) external {
        require(msg.sender == owner);
        MockERC20 t = MockERC20(token);
        uint256 b = t.balanceOf(address(this));
        if (b > 0) t.transfer(owner, b);
    }
}
