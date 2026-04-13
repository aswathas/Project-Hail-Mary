// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

/**
 * @title SimpleDEX
 * @notice Minimal AMM for swapping governance token to ETH/WETH.
 */
contract SimpleDEX {
    MockERC20 public token;
    uint256 public tokenReserve;
    uint256 public ethReserve;

    event Swap(address indexed trader, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event AddLiquidity(address indexed provider, uint256 tokenAmount, uint256 ethAmount);

    constructor(address _token) {
        token = MockERC20(_token);
    }

    function addLiquidity(uint256 tokenAmount) external payable {
        token.transferFrom(msg.sender, address(this), tokenAmount);
        tokenReserve += tokenAmount;
        ethReserve += msg.value;
        emit AddLiquidity(msg.sender, tokenAmount, msg.value);
    }

    function swapTokenForETH(uint256 tokenAmount) external returns (uint256 ethOut) {
        ethOut = (tokenAmount * ethReserve) / (tokenReserve + tokenAmount);
        token.transferFrom(msg.sender, address(this), tokenAmount);
        tokenReserve += tokenAmount;
        ethReserve -= ethOut;
        payable(msg.sender).transfer(ethOut);
        emit Swap(msg.sender, address(token), address(0), tokenAmount, ethOut);
    }

    receive() external payable {}
}
