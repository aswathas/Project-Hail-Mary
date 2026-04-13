// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title SimpleOracle
 * @notice A naive oracle that reads price from a DEX pool spot price.
 *         Vulnerable to flash loan manipulation.
 */
contract SimpleOracle {
    address public pool;
    address public owner;

    event PriceQueried(uint256 price, address querier);

    constructor(address _pool) {
        pool = _pool;
        owner = msg.sender;
    }

    function getPrice() external returns (uint256) {
        (bool success, bytes memory data) = pool.call(
            abi.encodeWithSignature("getSpotPrice()")
        );
        require(success, "Price query failed");
        uint256 price = abi.decode(data, (uint256));
        emit PriceQueried(price, msg.sender);
        return price;
    }
}
