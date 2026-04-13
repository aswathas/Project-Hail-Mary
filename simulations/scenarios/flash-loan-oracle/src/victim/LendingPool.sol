// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

interface IOracle {
    function getPrice() external returns (uint256);
}

/**
 * @title LendingPool
 * @notice Simplified lending pool that uses oracle for collateral valuation.
 *         Vulnerable because the oracle reads manipulable spot price.
 */
contract LendingPool {
    MockERC20 public collateralToken;
    MockERC20 public borrowToken;
    IOracle public oracle;
    address public owner;

    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debt;

    event CollateralDeposited(address indexed user, uint256 amount);
    event Borrowed(address indexed user, uint256 amount);
    event Repaid(address indexed user, uint256 amount);
    event Liquidated(address indexed user, address indexed liquidator, uint256 amount);

    constructor(address _collateral, address _borrow, address _oracle) {
        collateralToken = MockERC20(_collateral);
        borrowToken = MockERC20(_borrow);
        oracle = IOracle(_oracle);
        owner = msg.sender;
    }

    function depositCollateral(uint256 amount) external {
        collateralToken.transferFrom(msg.sender, address(this), amount);
        collateral[msg.sender] += amount;
        emit CollateralDeposited(msg.sender, amount);
    }

    function borrow(uint256 amount) external {
        uint256 price = oracle.getPrice();
        uint256 collateralValue = (collateral[msg.sender] * price) / 1e18;
        uint256 maxBorrow = (collateralValue * 80) / 100; // 80% LTV
        require(debt[msg.sender] + amount <= maxBorrow, "Exceeds borrow limit");

        debt[msg.sender] += amount;
        borrowToken.transfer(msg.sender, amount);
        emit Borrowed(msg.sender, amount);
    }

    function repay(uint256 amount) external {
        borrowToken.transferFrom(msg.sender, address(this), amount);
        debt[msg.sender] -= amount;
        emit Repaid(msg.sender, amount);
    }

    function seedLiquidity(uint256 amount) external {
        borrowToken.transferFrom(msg.sender, address(this), amount);
    }
}
