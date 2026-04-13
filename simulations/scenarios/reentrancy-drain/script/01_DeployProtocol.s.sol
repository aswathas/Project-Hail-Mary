// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/VulnerableVault.sol";

contract DeployProtocol is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);

        VulnerableVault vault = new VulnerableVault();
        console.log("VulnerableVault deployed at:", address(vault));

        vm.stopBroadcast();
    }
}
