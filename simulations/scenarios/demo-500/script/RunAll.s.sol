// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/MockERC20.sol";
import "../src/VulnerableVault.sol";
import "../src/ReentrancyAttacker.sol";
import "../src/SimpleDEX.sol";
import "../src/SandwichAttacker.sol";

/**
 * RunAll — ~500-transaction demo simulation.
 *
 * Attack 1: Reentrancy drain on VulnerableVault  (AP-005)
 * Attack 2: MEV sandwich on SimpleDEX            (AP-014)
 *
 * Run with:
 *   forge script script/RunAll.s.sol \
 *     --rpc-url http://127.0.0.1:8545 \
 *     --broadcast \
 *     --private-key $DEPLOYER_KEY \
 *     -vv
 */
contract RunAll is Script {
    // ── accounts ───────────────────────────────────────────────────────────
    // Anvil default private keys (deterministic)
    uint256 constant PK_DEPLOYER  = 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
    uint256 constant PK_ATTACKER  = 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d;
    uint256 constant PK_SANDWICH  = 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a;
    uint256 constant PK_USER1     = 0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6;
    uint256 constant PK_USER2     = 0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a;
    uint256 constant PK_USER3     = 0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba;
    uint256 constant PK_USER4     = 0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e;
    uint256 constant PK_USER5     = 0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356;
    uint256 constant PK_USER6     = 0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97;
    uint256 constant PK_USER7     = 0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6;

    address deployer;
    address attacker;
    address sandwichBot;
    address[8] users;

    MockERC20       tokenA;
    MockERC20       tokenB;
    VulnerableVault vault;
    ReentrancyAttacker reAttacker;
    SimpleDEX       dex;
    SandwichAttacker sandwichAttacker;

    uint256 constant TOKEN_UNIT   = 1e18;
    uint256 constant VAULT_SEED   = 0.5 ether;    // each user deposits into vault
    uint256 constant ATTACK_SEED  = 0.1 ether;    // reentrancy seed per iteration
    uint256 constant SWAP_AMOUNT  = 100 * TOKEN_UNIT;
    uint256 constant LIQUIDITY_A  = 100_000 * TOKEN_UNIT;
    uint256 constant LIQUIDITY_B  = 100_000 * TOKEN_UNIT;

    function run() external {
        deployer     = vm.addr(PK_DEPLOYER);
        attacker     = vm.addr(PK_ATTACKER);
        sandwichBot  = vm.addr(PK_SANDWICH);
        users[0]     = vm.addr(PK_USER1);
        users[1]     = vm.addr(PK_USER2);
        users[2]     = vm.addr(PK_USER3);
        users[3]     = vm.addr(PK_USER4);
        users[4]     = vm.addr(PK_USER5);
        users[5]     = vm.addr(PK_USER6);
        users[6]     = vm.addr(PK_USER7);
        users[7]     = vm.addr(PK_DEPLOYER); // deployer doubles as user 8

        // ── Phase 0: Deploy contracts (~8 txs) ───────────────────────────
        vm.startBroadcast(PK_DEPLOYER);
        tokenA     = new MockERC20("AlphaToken", "ALPHA", 18);
        tokenB     = new MockERC20("BetaToken",  "BETA",  18);
        vault      = new VulnerableVault();
        dex        = new SimpleDEX(address(tokenA), address(tokenB));

        // Seed liquidity for DEX
        tokenA.mint(deployer, LIQUIDITY_A * 2);
        tokenB.mint(deployer, LIQUIDITY_B * 2);
        tokenA.approve(address(dex), LIQUIDITY_A);
        tokenB.approve(address(dex), LIQUIDITY_B);
        dex.addLiquidity(LIQUIDITY_A, LIQUIDITY_B);
        vm.stopBroadcast();

        // ── Phase 1: Mint tokens to all participants (~20 txs) ───────────
        vm.startBroadcast(PK_DEPLOYER);
        for (uint256 i = 0; i < 8; i++) {
            tokenA.mint(users[i], 5_000 * TOKEN_UNIT);
            tokenB.mint(users[i], 5_000 * TOKEN_UNIT);
        }
        tokenA.mint(attacker,    1_000 * TOKEN_UNIT);
        tokenB.mint(attacker,    1_000 * TOKEN_UNIT);
        tokenA.mint(sandwichBot, 10_000 * TOKEN_UNIT);
        tokenB.mint(sandwichBot, 10_000 * TOKEN_UNIT);
        vm.stopBroadcast();

        // ── Phase 2: Normal vault + DEX activity (~150 txs) ──────────────
        _normalActivity(20);

        // ── Phase 3: Deploy attacker contracts (~2 txs) ──────────────────
        vm.startBroadcast(PK_ATTACKER);
        reAttacker = new ReentrancyAttacker(address(vault));
        vm.stopBroadcast();

        vm.startBroadcast(PK_SANDWICH);
        sandwichAttacker = new SandwichAttacker(address(dex));
        // Fund sandwich attacker with tokens
        vm.stopBroadcast();

        vm.startBroadcast(PK_DEPLOYER);
        tokenA.mint(address(sandwichAttacker), 5_000 * TOKEN_UNIT);
        tokenB.mint(address(sandwichAttacker), 5_000 * TOKEN_UNIT);
        vm.stopBroadcast();

        // ── Phase 4: More normal activity (~100 txs) ─────────────────────
        _normalActivity(12);

        // ── Phase 5: ATTACK 1 — Reentrancy drain (~15 txs) ───────────────
        _reentrancyAttack();

        // ── Phase 6: Cover traffic after attack 1 (~60 txs) ──────────────
        _normalActivity(7);

        // ── Phase 7: ATTACK 2 — MEV sandwich x5 (~30 txs) ────────────────
        _sandwichAttack(5);

        // ── Phase 8: Attacker disperses funds + more cover (~50 txs) ─────
        _disperseFunds();
        _normalActivity(6);
    }

    // ── Normal activity: rounds × (8 vault + 8 dex swaps) = rounds×16 txs ──
    function _normalActivity(uint256 rounds) internal {
        uint256[8] memory pks;
        pks[0] = PK_USER1; pks[1] = PK_USER2; pks[2] = PK_USER3; pks[3] = PK_USER4;
        pks[4] = PK_USER5; pks[5] = PK_USER6; pks[6] = PK_USER7; pks[7] = PK_DEPLOYER;

        for (uint256 r = 0; r < rounds; r++) {
            for (uint256 i = 0; i < 8; i++) {
                address user = users[i];
                uint256 pk   = pks[i];

                // Vault deposit
                vm.startBroadcast(pk);
                vault.deposit{value: VAULT_SEED}();
                vm.stopBroadcast();

                // DEX swap A→B (approve + swap = 2 txs)
                vm.startBroadcast(pk);
                tokenA.approve(address(dex), SWAP_AMOUNT);
                dex.swap(address(tokenA), SWAP_AMOUNT);
                vm.stopBroadcast();
            }

            // Every other round, half the users withdraw from vault (4 extra txs)
            if (r % 2 == 1) {
                for (uint256 i = 0; i < 4; i++) {
                    vm.startBroadcast(pks[i]);
                    uint256 bal = vault.balances(users[i]);
                    if (bal >= VAULT_SEED) {
                        vault.withdraw(VAULT_SEED);
                    }
                    vm.stopBroadcast();
                }
            }
        }
    }

    // ── Reentrancy drain attack (~15 txs) ────────────────────────────────────
    function _reentrancyAttack() internal {
        // First fatten the vault so reentrancy gets more loops
        for (uint256 i = 0; i < 5; i++) {
            vm.startBroadcast(_userPk(i % 8));
            vault.deposit{value: 1 ether}();
            vm.stopBroadcast();
        }

        // Execute reentrancy — 3 waves with different seeds
        for (uint256 wave = 0; wave < 3; wave++) {
            vm.startBroadcast(PK_ATTACKER);
            reAttacker.attack{value: ATTACK_SEED}();
            vm.stopBroadcast();

            // Drain collected ETH back to attacker EOA
            vm.startBroadcast(PK_ATTACKER);
            reAttacker.withdraw();
            vm.stopBroadcast();
        }
    }

    // ── MEV sandwich attack (iterations × ~4 txs each) ───────────────────────
    function _sandwichAttack(uint256 iterations) internal {
        uint256 sandwichAmount = 200 * TOKEN_UNIT;
        uint256 victimAmount   = 50  * TOKEN_UNIT;

        for (uint256 i = 0; i < iterations; i++) {
            address victim   = users[i % 8];
            uint256 victimPk = _userPk(i % 8);

            // Front-run: sandwich bot swaps A→B before victim
            vm.startBroadcast(PK_SANDWICH);
            sandwichAttacker.frontrun(address(tokenA), sandwichAmount);
            vm.stopBroadcast();

            // Victim swap (the "sandwiched" transaction)
            vm.startBroadcast(victimPk);
            tokenA.approve(address(dex), victimAmount);
            dex.swap(address(tokenA), victimAmount);
            vm.stopBroadcast();

            // Back-run: sandwich bot swaps B→A after victim
            vm.startBroadcast(PK_SANDWICH);
            sandwichAttacker.backrun(address(tokenB), sandwichAmount);
            vm.stopBroadcast();
        }

        // Drain all accumulated profits at end (not per-iteration — avoids depleting funds)
        vm.startBroadcast(PK_SANDWICH);
        sandwichAttacker.drain(address(tokenA));
        sandwichAttacker.drain(address(tokenB));
        vm.stopBroadcast();
    }

    // ── Attacker moves ETH to fresh addresses to obscure trail ───────────────
    function _disperseFunds() internal {
        address fresh1 = address(uint160(uint256(keccak256("fresh1"))));
        address fresh2 = address(uint160(uint256(keccak256("fresh2"))));

        vm.startBroadcast(PK_ATTACKER);
        uint256 half = attacker.balance / 2;
        if (half > 0) {
            payable(fresh1).transfer(half / 2);
            payable(fresh2).transfer(half / 2);
        }
        vm.stopBroadcast();

        // Sandwich bot disperses tokens
        vm.startBroadcast(PK_SANDWICH);
        uint256 taBal = tokenA.balanceOf(sandwichBot);
        uint256 tbBal = tokenB.balanceOf(sandwichBot);
        if (taBal > TOKEN_UNIT) tokenA.transfer(fresh1, taBal / 2);
        if (tbBal > TOKEN_UNIT) tokenB.transfer(fresh2, tbBal / 2);
        vm.stopBroadcast();
    }

    function _userPk(uint256 idx) internal pure returns (uint256) {
        uint256[8] memory pks;
        pks[0] = PK_USER1; pks[1] = PK_USER2; pks[2] = PK_USER3; pks[3] = PK_USER4;
        pks[4] = PK_USER5; pks[5] = PK_USER6; pks[6] = PK_USER7; pks[7] = PK_DEPLOYER;
        return pks[idx];
    }
}
