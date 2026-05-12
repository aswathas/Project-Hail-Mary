# 10. Attack-pattern catalog (38 patterns)

Patterns combine multiple signals in sequence. Each pattern lives in
`detection/patterns/` as a `.eql` file named `AP-NNN_short_slug.eql`.
The `pattern_id` written into `forensics` (layer: alert) is the `AP-NNN`
prefix.

The auto-generated table below is rebuilt by `make catalogs` from
`detection/patterns/*.eql`:

\pagebreak

{{< include ../_generated/patterns_catalog.md >}}

## 10.1 Reentrancy family (AP-001..AP-004)

| Pattern | Required signals | Scenario it detects |
|---------|------------------|---------------------|
| `AP-001 classic_reentrancy` | `flashloan_bracket_detected` (optional) → `cross_function_reentry` → `drain_ratio_exceeded` | Vanilla recursive `withdraw` that drains a vault. **Tested by `reentrancy-drain` scenario.** |
| `AP-002 cross_function_reentrancy` | `cross_function_reentry` → `storage_update_delay` → `drain_ratio_exceeded` | Reentrancy via a *different* function on the same contract. |
| `AP-003 read_only_reentrancy` | `cross_contract_state_dependency` → `price_read_during_callback` → loss event | Read-only reentrancy across two protocols. |
| `AP-004 erc777_hook_reentrancy` | `hook_callback_detected` → `cross_function_reentry` → `drain_ratio_exceeded` | ERC777 `tokensReceived` hook triggers reentrancy. |

## 10.2 Flash-loan family (AP-005..AP-008)

| Pattern | Required signals | Scenario |
|---------|------------------|----------|
| `AP-005 classic_flash_loan` | `flashloan_bracket_detected` → `value_drain_per_depth` | Generic flash-loan-funded exploit. |
| `AP-006 flash_loan_oracle` | `flashloan_bracket_detected` → `spot_price_manipulation` → `drain_ratio_exceeded` | Borrow → manipulate spot → drain. **Tested by `flash-loan-oracle` scenario.** |
| `AP-007 flash_loan_governance` | `flashloan_bracket_detected` → governance vote → execute | Use flash-loaned voting power to pass a malicious proposal. |
| `AP-008 multi_pool_flash_loan` | ≥ 2 `flashloan_bracket_detected` → cascade | Compose loans from multiple sources. |

## 10.3 Oracle family (AP-009..AP-011)

| Pattern | Required signals |
|---------|------------------|
| `AP-009 amm_spot_price` | `flashloan_bracket_detected` → `spot_price_manipulation` → liquidation/swap |
| `AP-010 twap_manipulation` | sustained `twap_drift_detected` over N blocks → exploit |
| `AP-011 multi_oracle_inconsistency` | `multi_oracle_divergence` → exploit |

## 10.4 Access / upgrade family (AP-012..AP-015)

| Pattern | Required signals | Scenario |
|---------|------------------|----------|
| `AP-012 ownership_hijack` | `ownership_transfer_then_drain` | **Tested by `admin-key-abuse`.** |
| `AP-013 uninitialized_proxy` | `proxy_implementation_change` → `initialize_on_live_contract` → drain | Classic UUPS / TransparentProxy abuse. |
| `AP-014 delegatecall_escalation` | `delegatecall_storage_write` → privileged call | **Touched by `mev-sandwich` for upgrade variant.** |
| `AP-015 selfdestruct_drain` | `selfdestruct_detected` → balance loss | Old contracts using `SELFDESTRUCT` as a treasury sweep. |

## 10.5 MEV / liquidation family (AP-016..AP-018)

| Pattern | Required signals | Scenario |
|---------|------------------|----------|
| `AP-016 sandwich_attack` | front-run swap → victim swap → back-run swap, same block | **Tested by `mev-sandwich`.** |
| `AP-017 frontrunning` | gas price > victim, same target tx in mempool | Generic front-running. |
| `AP-018 liquidation_manipulation` | `spot_price_manipulation` → `liquidation_cascade_trigger` | Manufactured liquidations. |

## 10.6 Token / rug family (AP-019..AP-024)

| Pattern | Required signals |
|---------|------------------|
| `AP-019 liquidity_rug` | `liquidity_removal_spike` → `value_dispersion` |
| `AP-020 mint_and_dump` | `mint_to_dump_ratio` → `rapid_token_dump` |
| `AP-021 infinite_approval_drain` | `approval_for_max_amount` → `token_balance_drain` |
| `AP-022 slow_rug` | governance change → fee bump → `value_dispersion` |
| `AP-023 donation_attack` | `donation_balance_inflation` → `vault_share_price_spike` |
| `AP-024 vault_inflation` | `donation_balance_inflation` → ERC-4626 `mint(low)` |

## 10.7 Signature / supply family (AP-025..AP-029)

| Pattern | Required signals |
|---------|------------------|
| `AP-025 permit_signature_abuse` | `permit_used_before_owner_approval` → drain |
| `AP-026 integer_overflow` | `integer_overflow_detected` |
| `AP-027 fee_on_transfer` | `fee_on_transfer_discrepancy` → accounting break |
| `AP-028 rebasing_token` | `rebasing_balance_manipulation` mid-call |
| `AP-029 signature_replay` | `eip712_replay_detected` → action |

## 10.8 Graph / cluster family (AP-030..AP-034)

| Pattern | Required signals |
|---------|------------------|
| `AP-030 attacker_deployment` | `contract_deployed_before_attack` → `same_block_deploy_and_attack` |
| `AP-031 fund_dispersion` | `fund_dispersion_post_attack` → `value_dispersion` |
| `AP-032 address_clustering` | `address_cluster_identified` + ≥ 1 alert |
| `AP-033 mixer_bridge_detection` | `mixer_interaction_detected` ∨ `bridge_interaction_detected` |
| `AP-034 cross_contract_collusion` | `contract_creator_linked` → coordinated drain |

## 10.9 Cross-cutting (AP-035..AP-038)

| Pattern | Required signals |
|---------|------------------|
| `AP-035 governance_manipulation` | `governance_instant_execution` ∨ flash-loan vote |
| `AP-036 liquidation_cascade` | `liquidation_cascade_trigger` + `spot_price_manipulation` |
| `AP-037 metamorphic_contract` | `selfdestruct_detected` → `create2_redeployment` |
| `AP-038 multiple_asset_sweep` | `multiple_asset_drain_same_tx` → `fund_dispersion_post_attack` |
