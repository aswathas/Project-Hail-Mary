// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";
import "../src/victim/MockUniswapPool.sol";
import "../src/victim/SimpleOracle.sol";
import "../src/victim/LendingPool.sol";
import "../src/attacker/FlashLoanAttacker.sol";

/**
 * @title RunAll
 * @notice Runs all 4 phases of the flash-loan-oracle scenario (~80 txs).
 */
contract RunAll is Script {
    MockERC20 public tokenA;
    MockERC20 public tokenB;
    MockUniswapPool public pool;
    SimpleOracle public oracle;
    LendingPool public lending;

    function run() external {
        _phase1_deploy();
        _phase2_liquidity();
        _phase2_collateralAndBorrow();
        _phase2_swapsAndRepay();
        _phase3_attack();
        _phase4_postAttack();
        console.log("All phases complete.");
    }

    function _phase1_deploy() internal {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);

        tokenA = new MockERC20("Wrapped Ether", "WETH", 18);
        tokenB = new MockERC20("USD Coin", "USDC", 18);
        pool = new MockUniswapPool(address(tokenA), address(tokenB));

        tokenA.mint(msg.sender, 1_000_000e18);
        tokenB.mint(msg.sender, 1_000_000_000e18);
        tokenA.approve(address(pool), 500_000e18);
        tokenB.approve(address(pool), 500_000_000e18);
        pool.addLiquidity(500_000e18, 500_000_000e18);

        oracle = new SimpleOracle(address(pool));
        lending = new LendingPool(address(tokenA), address(tokenB), address(oracle));
        tokenB.mint(address(lending), 200_000_000e18);

        console.log("WETH:", address(tokenA));
        console.log("USDC:", address(tokenB));
        console.log("Pool:", address(pool));
        console.log("Oracle:", address(oracle));
        console.log("LendingPool:", address(lending));

        vm.stopBroadcast();
    }

    function _phase2_liquidity() internal {
        uint256[5] memory keys;
        keys[0] = vm.envUint("USER1_KEY");
        keys[1] = vm.envUint("USER2_KEY");
        keys[2] = vm.envUint("USER3_KEY");
        keys[3] = vm.envUint("USER4_KEY");
        keys[4] = vm.envUint("USER5_KEY");

        address poolAddr = address(pool);
        uint256[5] memory liqA = [uint256(1_000e18), 800e18, 1_500e18, 700e18, 900e18];
        uint256[5] memory liqB = [uint256(1_000_000e18), 800_000e18, 1_500_000e18, 700_000e18, 900_000e18];
        uint256[5] memory liq2A = [uint256(500e18), 300e18, 400e18, 250e18, 450e18];
        uint256[5] memory liq2B = [uint256(500_000e18), 300_000e18, 400_000e18, 250_000e18, 450_000e18];
        uint256[5] memory liq3A = [uint256(200e18), 600e18, 100e18, 350e18, 550e18];
        uint256[5] memory liq3B = [uint256(200_000e18), 600_000e18, 100_000e18, 350_000e18, 550_000e18];

        for (uint256 i = 0; i < 5; i++) {
            vm.startBroadcast(keys[i]);
            tokenA.mint(msg.sender, 10_000e18);
            tokenB.mint(msg.sender, 10_000_000e18);
            tokenA.approve(poolAddr, 10_000e18);
            tokenB.approve(poolAddr, 10_000_000e18);
            pool.addLiquidity(liqA[i], liqB[i]);
            pool.addLiquidity(liq2A[i], liq2B[i]);
            pool.addLiquidity(liq3A[i], liq3B[i]);
            vm.stopBroadcast();
        }
    }

    function _phase2_collateralAndBorrow() internal {
        address lendingAddr = address(lending);

        uint256 u1 = vm.envUint("USER1_KEY");
        uint256 u2 = vm.envUint("USER2_KEY");
        uint256 u3 = vm.envUint("USER3_KEY");
        uint256 u4 = vm.envUint("USER4_KEY");
        uint256 u5 = vm.envUint("USER5_KEY");

        vm.startBroadcast(u1);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(500e18);
        lending.borrow(200_000e18);
        lending.depositCollateral(300e18);
        lending.borrow(100_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u2);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(400e18);
        lending.borrow(150_000e18);
        lending.depositCollateral(200e18);
        lending.borrow(80_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u3);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(600e18);
        lending.borrow(250_000e18);
        lending.depositCollateral(100e18);
        lending.borrow(40_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u4);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(350e18);
        lending.borrow(140_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u5);
        tokenA.approve(lendingAddr, 10_000e18);
        lending.depositCollateral(450e18);
        lending.borrow(180_000e18);
        lending.depositCollateral(250e18);
        lending.borrow(100_000e18);
        vm.stopBroadcast();
    }

    function _phase2_swapsAndRepay() internal {
        address tokenAAddr = address(tokenA);
        address lendingAddr = address(lending);

        uint256 u1 = vm.envUint("USER1_KEY");
        uint256 u2 = vm.envUint("USER2_KEY");
        uint256 u3 = vm.envUint("USER3_KEY");
        uint256 u4 = vm.envUint("USER4_KEY");
        uint256 u5 = vm.envUint("USER5_KEY");

        // 10 swaps
        vm.startBroadcast(u1);
        pool.swap(tokenAAddr, 50e18);
        pool.swap(tokenAAddr, 30e18);
        vm.stopBroadcast();

        vm.startBroadcast(u2);
        pool.swap(tokenAAddr, 80e18);
        pool.swap(tokenAAddr, 20e18);
        vm.stopBroadcast();

        vm.startBroadcast(u3);
        pool.swap(tokenAAddr, 40e18);
        pool.swap(tokenAAddr, 60e18);
        vm.stopBroadcast();

        vm.startBroadcast(u4);
        pool.swap(tokenAAddr, 25e18);
        pool.swap(tokenAAddr, 35e18);
        vm.stopBroadcast();

        vm.startBroadcast(u5);
        pool.swap(tokenAAddr, 45e18);
        pool.swap(tokenAAddr, 55e18);
        vm.stopBroadcast();

        // 5 repayments
        vm.startBroadcast(u1);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(50_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u2);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(30_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u3);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(40_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u4);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(20_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u5);
        tokenB.approve(lendingAddr, 10_000_000e18);
        lending.repay(25_000e18);
        vm.stopBroadcast();
    }

    function _phase3_attack() internal {
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        address tokenBAddr = address(tokenB);
        address poolAddr = address(pool);

        vm.startBroadcast(attackerKey);

        FlashLoanAttacker attacker = new FlashLoanAttacker(
            poolAddr, address(lending), address(tokenA), tokenBAddr
        );
        attacker.attack(400_000e18);
        console.log("Flash loan oracle attack executed");

        attacker.withdraw(tokenBAddr);
        attacker.withdraw(address(tokenA));

        // Convert stolen USDC via multiple swaps
        uint256 stolenUSDC = tokenB.balanceOf(msg.sender);
        if (stolenUSDC > 0) {
            tokenB.approve(poolAddr, stolenUSDC);
            uint256 chunk = stolenUSDC / 5;
            if (chunk > 0) {
                pool.swap(tokenBAddr, chunk);
                pool.swap(tokenBAddr, chunk);
                pool.swap(tokenBAddr, chunk);
                pool.swap(tokenBAddr, chunk);
                pool.swap(tokenBAddr, chunk);
            }
        }

        vm.stopBroadcast();
    }

    function _phase4_postAttack() internal {
        uint256 u1 = vm.envUint("USER1_KEY");
        uint256 u2 = vm.envUint("USER2_KEY");
        uint256 u3 = vm.envUint("USER3_KEY");
        address tokenAAddr = address(tokenA);
        address poolAddr = address(pool);
        address lendingAddr = address(lending);

        vm.startBroadcast(u1);
        tokenA.mint(msg.sender, 1_000e18);
        tokenA.approve(poolAddr, 1_000e18);
        pool.swap(tokenAAddr, 10e18);
        pool.swap(tokenAAddr, 5e18);
        vm.stopBroadcast();

        vm.startBroadcast(u2);
        tokenB.mint(msg.sender, 100_000e18);
        tokenB.approve(lendingAddr, 100_000e18);
        lending.repay(30_000e18);
        lending.repay(20_000e18);
        vm.stopBroadcast();

        vm.startBroadcast(u3);
        tokenA.mint(msg.sender, 500e18);
        tokenA.approve(poolAddr, 500e18);
        pool.swap(tokenAAddr, 5e18);
        pool.swap(tokenAAddr, 3e18);
        vm.stopBroadcast();
    }
}
