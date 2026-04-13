// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title UserActivity
 * @notice Generates realistic normal traffic on a protocol.
 *         Called during Phase 2 of each scenario to create noise
 *         that ChainSentinel must filter through.
 */
contract UserActivity {
    event UserDeposit(address indexed user, uint256 amount);
    event UserWithdraw(address indexed user, uint256 amount);
    event UserTransfer(address indexed from, address indexed to, uint256 amount);

    /// @notice Simulate a normal user depositing into a vault/pool
    function simulateDeposit(address vault, uint256 amount) external payable {
        (bool success,) = vault.call{value: amount}(
            abi.encodeWithSignature("deposit()")
        );
        require(success, "Deposit failed");
        emit UserDeposit(msg.sender, amount);
    }

    /// @notice Simulate a normal user withdrawing from a vault/pool
    function simulateWithdraw(address vault, uint256 amount) external {
        (bool success,) = vault.call(
            abi.encodeWithSignature("withdraw(uint256)", amount)
        );
        require(success, "Withdraw failed");
        emit UserWithdraw(msg.sender, amount);
    }

    /// @notice Simulate ETH transfers between users
    function simulateTransfer(address payable to) external payable {
        to.transfer(msg.value);
        emit UserTransfer(msg.sender, to, msg.value);
    }

    receive() external payable {}
}
