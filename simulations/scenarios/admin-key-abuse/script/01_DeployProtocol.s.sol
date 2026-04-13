// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/GovernanceToken.sol";
import "../src/victim/SimpleDEX.sol";

/**
 * @title DeployProtocol
 * @notice Phase 1: Deploy GovernanceToken + SimpleDEX + seed liquidity (~3 txs).
 */
contract DeployProtocol is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);

        // Deploy governance token with 1M initial supply to deployer
        GovernanceToken govToken = new GovernanceToken("GovToken", "GOV", 1_000_000e18);
        console.log("GovernanceToken:", address(govToken));

        // Deploy DEX for GOV/ETH
        SimpleDEX dex = new SimpleDEX(address(govToken));
        console.log("SimpleDEX:", address(dex));

        // Seed DEX with initial liquidity: 500k GOV + 100 ETH
        govToken.approve(address(dex), 500_000e18);
        dex.addLiquidity{value: 100 ether}(500_000e18);

        vm.stopBroadcast();
    }
}
