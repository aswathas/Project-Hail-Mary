// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IVaultActivity {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
}

/**
 * @title NormalUsers
 * @notice Simulates normal user behavior on VulnerableVault.
 *         Multiple users deposit and some withdraw small amounts.
 */
contract NormalUsers {
    IVaultActivity public vault;

    constructor(address _vault) {
        vault = IVaultActivity(_vault);
    }

    function depositMultiple() external payable {
        uint256 perUser = msg.value / 5;
        for (uint256 i = 0; i < 5; i++) {
            vault.deposit{value: perUser}();
        }
    }

    function smallWithdraw(uint256 amount) external {
        vault.withdraw(amount);
    }

    receive() external payable {}
}
