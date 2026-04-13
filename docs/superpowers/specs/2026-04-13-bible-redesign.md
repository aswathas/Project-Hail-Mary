# ChainSentinel Bible Redesign — Full Specification

**Date:** 2026-04-13  
**Status:** APPROVED  
**Approach:** B — Incremental Bible Alignment with Phased Build  

---

## 1. Overview

Restructure ChainSentinel's detection framework to match the Forensic Bible (v2) exactly. Every derived log, signal, and attack pattern in the Bible maps 1:1 to a code file. The forensic team treats the Bible as gospel — code must match it verbatim.

**Final counts:**
- 35 derived logs (10 raw log types as input)
- 58 detection signals across 8 families
- 38 attack patterns across 9 families
- 3 simulation scenarios producing ~200 transactions

---

## 2. Derived Logs (35)

### Architecture Change
Replace `pipeline/derived.py` (monolith) with `pipeline/derived/` package. One file per derived log. Each exports:

```python
async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]
```

### Complete Derived Log Registry

#### Core (6 logs — always available)
| # | derived_type | File | Priority | Raw Inputs |
|---|---|---|---|---|
| 1 | contract_deployments | contract_deployments.py | High | transactions_raw, receipts, blocks |
| 2 | contract_interactions | contract_interactions.py | High | transactions_raw, receipts, blocks |
| 3 | gas_analysis | gas_analysis.py | Low | blocks, receipts |
| 4 | eth_transfers | eth_transfers.py | High | balance_diffs |
| 5 | failed_transactions | failed_transactions.py | High | receipts, transactions_raw |
| 6 | enriched_event_logs | enriched_event_logs.py | High | event_logs_raw + ABI |

#### Trace-Dependent (8 logs — require call_traces_raw / archive node / Anvil)
| # | derived_type | File | Priority | Raw Inputs |
|---|---|---|---|---|
| 7 | internal_calls | internal_calls.py | High | call_traces_raw |
| 8 | execution_structure | execution_structure.py | CRITICAL | call_traces_raw |
| 9 | reentrancy_patterns | reentrancy_patterns.py | High | execution_structure (derived-from-derived) |
| 10 | value_flow_intra_tx | value_flow_intra_tx.py | CRITICAL | call_traces_raw, balance_diffs |
| 11 | state_delta_per_tx | state_delta_per_tx.py | CRITICAL | storage_diffs, state_diffs |
| 12 | event_sequence | event_sequence.py | CRITICAL | event_logs_raw + ABI |
| 13 | failed_internals | failed_internals.py | High | call_traces_raw, receipts |
| 14 | price_reads | price_reads.py | High | call_traces_raw, event_logs_raw |

#### Behavioural (8 logs)
| # | derived_type | File | Priority | Raw Inputs |
|---|---|---|---|---|
| 15 | storage_mutations | storage_mutations.py | High | storage_diffs |
| 16 | address_activity_summary | address_activity_summary.py | High | transactions, receipts, balance_diffs |
| 17 | transaction_timeline | transaction_timeline.py | High | all raw |
| 18 | nonce_tracking | nonce_tracking.py | Medium | state_diffs |
| 19 | address_first_contact | address_first_contact.py | High | transactions_raw, blocks |
| 20 | deployment_to_attack | deployment_to_attack.py | High | transactions, receipts, blocks |
| 21 | block_address_activity | block_address_activity.py | High | transactions, blocks, events |
| 22 | failed_attempt_history | failed_attempt_history.py | High | receipts, transactions_raw |

#### Graph (6 logs)
| # | derived_type | File | Priority | Raw Inputs |
|---|---|---|---|---|
| 23 | value_flow_graph | value_flow_graph.py | High | transactions, call_traces |
| 24 | address_interaction_graph | address_interaction_graph.py | Medium | transactions, call_traces |
| 25 | fund_hop_chains | fund_hop_chains.py | High | balance_diffs, transactions |
| 26 | contract_creator_graph | contract_creator_graph.py | High | transactions, receipts, state_diffs |
| 27 | balance_spike_registry | balance_spike_registry.py | High | balance_diffs, address_activity |
| 28 | multi_token_balance_snapshot | multi_token_balance_snapshot.py | High | events, balance_diffs |

#### Specialist (7 logs — client/protocol dependent)
| # | derived_type | File | Priority | Raw Inputs |
|---|---|---|---|---|
| 29 | token_transfer_graph | token_transfer_graph.py | Medium | token_transfers / events + ABI |
| 30 | approval_registry | approval_registry.py | High | event_logs_raw + ABI |
| 31 | governance_actions | governance_actions.py | Medium | event_logs_raw + ABI |
| 32 | liquidation_events | liquidation_events.py | Medium | event_logs_raw + ABI |
| 33 | permit_usage_log | permit_usage_log.py | Medium | call_traces, events |
| 34 | donation_tracker | donation_tracker.py | Medium | call_traces, transactions |
| 35 | share_price_history | share_price_history.py | Medium | events, balance_diffs, storage |

### Build Order Dependencies
- `execution_structure` must build before `reentrancy_patterns`
- `address_activity_summary` must build before `balance_spike_registry`
- All Core logs build before Trace/Behavioural/Graph/Specialist

---

## 3. Detection Signals (58)

Each signal = one `.esql` file in `detection/signals/{family}/`. File naming matches Bible signal name exactly.

### Signal Registry

#### Structural Family (10 signals)
| Signal Name | Severity | Weight | Derived Needed | Detects |
|---|---|---|---|---|
| recursive_depth_pattern | CRIT | W3 | execution_structure | Same address at depth N and N+2+ in same tx |
| cross_function_reentry | CRIT | W3 | execution_structure, state_delta_per_tx | Same victim, different func selectors at different depths |
| value_drain_per_depth | CRIT | W3 | execution_structure, value_flow_intra_tx | ETH flows OUT at each reentrancy depth |
| storage_update_delay | CRIT | W3 | state_delta_per_tx, execution_structure | Balance mapping NOT updated between successive calls |
| hook_callback_detected | HIGH | W2 | execution_structure, event_sequence | tokensReceived() called before transfer completes |
| delegatecall_storage_write | CRIT | W3 | execution_structure, state_delta_per_tx | DELEGATECALL + storage slots in caller modified |
| proxy_implementation_change | CRIT | W3 | storage_mutations, state_delta_per_tx | EIP-1967 implementation slot changed |
| selfdestruct_detected | CRIT | W3 | execution_structure, failed_internals | SELFDESTRUCT opcode executed |
| flashloan_bracket_detected | CRIT | W3 | execution_structure, value_flow_intra_tx, event_sequence | Large value out depth 0, operations depth 1+, value returns by tx end |
| initialize_on_live_contract | CRIT | W3 | execution_structure, state_delta_per_tx | initialize() on contract with non-zero state |
| create2_redeployment | CRIT | W3 | execution_structure, contract_deployments | Same address: code → no code → different code |

#### Value Family (9 signals)
| Signal Name | Severity | Weight | Derived Needed | Detects |
|---|---|---|---|---|
| large_value_inflow_spike | HIGH | W2 | value_flow_intra_tx, eth_transfers, balance_spike_registry | ETH >10x 30-block rolling avg inflow |
| drain_ratio_exceeded | CRIT | W3 | value_flow_intra_tx, eth_transfers | Value out >80% of contract balance in single tx |
| value_concentration | LOW | W1 | value_flow_graph, fund_hop_chains, eth_transfers | 3+ addresses send to same address within 10 blocks |
| value_dispersion | HIGH | W2 | value_flow_graph, fund_hop_chains, balance_spike_registry | Single address sends to 3+ fresh addresses within 50 blocks |
| net_negative_contract_balance | CRIT | W3 | value_flow_intra_tx, event_sequence, eth_transfers | Balance dropped with no Withdrawn event |
| mint_to_dump_ratio | CRIT | W3 | event_sequence, value_flow_intra_tx, token_transfer_graph | Mint >20% supply AND dump on DEX within 2 blocks |
| liquidity_removal_spike | CRIT | W3 | value_flow_intra_tx, event_sequence, eth_transfers | LP removal >80% of pool |
| vault_share_price_spike | CRIT | W3 | share_price_history, value_flow_intra_tx | Share price +500% in single tx |
| multiple_asset_drain_same_tx | HIGH | W2 | token_transfer_graph, eth_transfers, multi_token_balance_snapshot | 3+ distinct token types drained from same contract in same tx |

#### Sequence Family (6 signals)
| Signal Name | Severity | Weight | Derived Needed | Detects |
|---|---|---|---|---|
| deposit_withdraw_same_tx | HIGH | W2 | event_sequence, enriched_event_logs | Deposit AND Withdraw for same address in same tx |
| event_order_violation | HIGH | W2 | event_sequence, enriched_event_logs | Events in wrong order (Withdrawn before Deposited) |
| duplicate_event_emission | CRIT | W3 | event_sequence, enriched_event_logs | Same event >1x from same contract for same user in same tx |
| missing_expected_event | CRIT | W3 | event_sequence, state_delta_per_tx, enriched_event_logs | State changed but expected event NOT emitted |
| event_parameter_mismatch | HIGH | W2 | event_sequence, state_delta_per_tx, value_flow_intra_tx | Event amount differs from actual balance change |
| ownership_transfer_then_drain | CRIT | W3 | event_sequence, state_delta_per_tx, value_flow_intra_tx | OwnershipTransferred AND drain in same tx |

#### Behavioural Family (8 signals)
| Signal Name | Severity | Weight | Derived Needed | Detects |
|---|---|---|---|---|
| new_address_first_interaction | LOW | W1 | address_first_contact, nonce_tracking, address_activity_summary | Nonce < 3 interacting with protocol for first time |
| contract_deployed_before_attack | HIGH | W2 | deployment_to_attack, contract_creator_graph, nonce_tracking | Contract deployed within 10 blocks before attack tx |
| address_funded_before_attack | HIGH | W2 | address_first_contact, address_activity_summary, fund_hop_chains | Wallet first funded within 50 blocks before deploy |
| nonce_gap_detected | LOW | W1 | nonce_tracking | Nonce jumps non-sequentially in single block |
| high_gas_anomaly | LOW | W1 | gas_analysis, execution_structure | Gas >3x avg for same function selector |
| failed_attempts_before_success | HIGH | W2 | failed_attempt_history, failed_transactions, failed_internals | 1+ failed txs against same target within 20 blocks before success |
| approval_for_max_amount | HIGH | W2 | approval_registry, contract_creator_graph | Max uint256 approval to unknown/fresh contract |
| same_block_deploy_and_attack | CRIT | W3 | deployment_to_attack | Contract deployed AND used to attack in SAME block |
| contract_size_anomaly | LOW | W1 | contract_deployments | Bytecode < 500 bytes or > 10KB (attacker contract profile) |

#### Oracle Family (7 signals)
| Signal Name | Severity | Weight | Derived Needed | Detects |
|---|---|---|---|---|
| price_read_during_callback | CRIT | W3 | price_reads, execution_structure | Oracle read while ETH send callback active in stack |
| spot_price_manipulation | CRIT | W3 | price_reads, value_flow_intra_tx | AMM spot price deviates >15% within same tx |
| reserve_ratio_spike | HIGH | W2 | price_reads, event_sequence, value_flow_intra_tx | Pool reserve ratio changes >20% in single tx |
| twap_drift_detected | HIGH | W2 | price_reads, block_address_activity, transaction_timeline | TWAP deviates from spot >10% over 10-block window |
| multi_oracle_divergence | CRIT | W3 | price_reads, execution_structure | 2+ oracles return prices diverging >10% |
| price_before_after_mismatch | HIGH | W2 | price_reads, transaction_timeline | Price at N-1 ≈ N+1 but differs >15% during tx |
| donation_balance_inflation | CRIT | W3 | donation_tracker, share_price_history | Direct ETH send causes share price to spike |

#### Graph Family (6 signals)
| Signal Name | Severity | Weight | Derived Needed | Detects |
|---|---|---|---|---|
| fund_dispersion_post_attack | HIGH | W2 | fund_hop_chains, value_flow_graph, balance_spike_registry | Funds sent to 3+ fresh addresses within 50 blocks |
| mixer_interaction_detected | CRIT | W3 | fund_hop_chains, value_flow_graph, address_interaction_graph | Fund hop reaches known mixer address |
| bridge_interaction_detected | CRIT | W3 | fund_hop_chains, value_flow_graph | Fund hop reaches known bridge address |
| address_cluster_identified | HIGH | W2 | address_interaction_graph, contract_creator_graph, fund_hop_chains | 2+ addresses same entity (common funder/deployer/timing) |
| contract_creator_linked | CRIT | W3 | contract_creator_graph, deployment_to_attack | Attack + victim-interacting contracts share same deployer |
| multi_hop_fund_trail | HIGH | W2 | fund_hop_chains, value_flow_graph, balance_spike_registry | Funds traceable through 3+ hops from exploit |

#### Additional Family (8 signals)
| Signal Name | Severity | Weight | Derived Needed | Detects |
|---|---|---|---|---|
| integer_overflow_detected | CRIT | W3 | state_delta_per_tx, storage_mutations | Value wraps around uint256 max. Note: only pre-0.8 or unchecked |
| liquidation_cascade_trigger | HIGH | W2 | liquidation_events, price_reads, block_address_activity | 3+ liquidations within 5 blocks of price manipulation |
| eip712_replay_detected | CRIT | W3 | permit_usage_log, event_sequence | Duplicate signature hash or expired deadline |
| fee_on_transfer_discrepancy | HIGH | W2 | token_transfer_graph, event_sequence | Sent != received in token transfer |
| rebasing_balance_manipulation | HIGH | W2 | storage_mutations, event_sequence | Balance changes without Transfer event |
| cross_contract_state_dependency | HIGH | W2 | execution_structure, state_delta_per_tx | STATICCALL reads stale state from modified contract |
| governance_instant_execution | CRIT | W3 | event_sequence, governance_actions | Proposal created AND executed in same tx/1 block |
| permit_used_before_owner_approval | CRIT | W3 | permit_usage_log, approval_registry, token_transfer_graph | permit() + transferFrom in same tx draining tokens |

---

## 4. Attack Patterns (38)

Each pattern = one `.eql` file in `detection/patterns/`. EQL sequence queries correlating signals.

### Pattern Registry

#### Reentrancy Family (4)
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-001 | Classic Reentrancy | A: Single Tx | recursive_depth + value_drain + storage_delay | ≥7 weight |
| AP-002 | Cross-Function Reentrancy | A: Single Tx | cross_function_reentry + storage_delay + deposit_withdraw | ≥7 weight |
| AP-003 | Read-Only Reentrancy | A: Single Tx | price_read_during_callback + value_drain + cross_contract_state | ≥7 weight |
| AP-004 | ERC777 Hook Reentrancy | A: Single Tx | hook_callback + storage_delay + recursive_depth | ≥5 weight |

#### Flash Loan Family (4)
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-005 | Classic Flash Loan Exploit | A: Single Tx | flashloan_bracket + large_value_inflow + drain_ratio | ≥7 weight |
| AP-006 | Flash Loan + Oracle Manipulation | A: Single Tx | flashloan_bracket + spot_price_manipulation + price_read + drain_ratio | ≥9 weight |
| AP-007 | Flash Loan + Governance Attack | A: Single Tx | flashloan_bracket + governance_instant_execution + drain_ratio | ≥7 weight |
| AP-008 | Multi-Pool Chained Flash Loan | A: Single Tx | flashloan_bracket (multiple) + large_value_inflow + value_concentration | ≥5 weight |

#### Oracle Manipulation Family (3)
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-009 | AMM Spot Price Manipulation | A: Single Tx | spot_price + price_read + reserve_ratio | ≥7 weight |
| AP-010 | TWAP Manipulation | B: Multi Tx | twap_drift + reserve_ratio + address_funded | ≥5 weight |
| AP-011 | Multi-Oracle Inconsistency | A: Single Tx | multi_oracle_divergence + price_before_after + drain_ratio | ≥5 weight |

#### Access Control Family (4)
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-012 | Ownership Hijack + Drain | A: Single Tx | ownership_transfer_then_drain + event_order + drain_ratio | ≥6 weight |
| AP-013 | Uninitialized Proxy Exploit | A: Single Tx | initialize_on_live + ownership_transfer + proxy_implementation | ≥6 weight |
| AP-014 | Delegatecall Privilege Escalation | A: Single Tx | delegatecall_storage_write + proxy_implementation + ownership_transfer | ≥6 weight |
| AP-015 | Selfdestruct Drain | A: Single Tx | selfdestruct_detected + net_negative + drain_ratio | ≥6 weight |

#### MEV / Sandwich Family (3)
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-016 | Sandwich Attack | B: Multi Tx | reserve_ratio + high_gas + fund_dispersion | ≥5 weight |
| AP-017 | Frontrunning | B: Multi Tx | high_gas + new_address_first + event_order | ≥3 weight |
| AP-018 | Liquidation Manipulation | B: Multi Tx | spot_price + reserve_ratio + liquidation_cascade | ≥7 weight |

#### Rug Pull Family (4)
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-019 | Liquidity Rug | A: Single Tx | liquidity_removal_spike + drain_ratio + address_funded | ≥5 weight |
| AP-020 | Mint and Dump | A: Single Tx | mint_to_dump + liquidity_removal + value_concentration | ≥7 weight |
| AP-021 | Infinite Approval Drain | A: Single Tx | approval_for_max + drain_ratio + contract_deployed | ≥5 weight |
| AP-022 | Slow Rug (Gradual Drain) | B/C: Extended | drain_ratio (cumulative) + address_funded + failed_attempts | ≥5 weight (Phase 2 — rolling window) |

#### Token Mechanism Family (6)
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-023 | Donation Attack | A: Single Tx | donation_balance_inflation + vault_share_price + net_negative | ≥5 weight |
| AP-024 | ERC4626 Vault Inflation | B: Multi Tx | vault_share_price + donation_inflation + large_value_inflow | ≥7 weight |
| AP-025 | Permit / EIP-2612 Signature Abuse | A: Single Tx | permit_used_before_owner + approval_for_max + drain_ratio | ≥6 weight |
| AP-026 | Integer Overflow Exploit | A: Single Tx | integer_overflow + event_parameter_mismatch + storage_delay | ≥3 weight |
| AP-027 | Fee-on-Transfer Token Exploit | A: Single Tx | fee_on_transfer_discrepancy + event_parameter_mismatch | ≥2 weight |
| AP-028 | Rebasing Token Exploit | A/B | rebasing_balance_manipulation + missing_expected_event | ≥2 weight |
| AP-029 | Signature Replay Attack | A/B | eip712_replay + nonce_gap + permit_used | ≥3 weight |

#### Graph / Attribution Family (5)
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-030 | Attacker Contract Deployment | C: Multi Addr | contract_deployed_before + address_funded + new_address_first | ≥5 weight |
| AP-031 | Fund Dispersion Post Attack | C: Multi Addr | fund_dispersion_post + value_dispersion + balance_spike | ≥4 weight |
| AP-032 | Address Clustering | C: Multi Addr | address_cluster + contract_creator_linked + address_funded | ≥4 weight |
| AP-033 | Mixer / Bridge Detection | C: Multi Addr | mixer_interaction + bridge_interaction + multi_hop | ≥3 weight |
| AP-034 | Cross-Contract Collusion | C: Multi Addr | address_cluster + contract_creator_linked + event_order | ≥6 weight |
| AP-035 | Governance Manipulation | A/B | governance_instant + flashloan_bracket + drain_ratio | ≥5 weight |
| AP-036 | Liquidation Cascade | B: Multi Tx | liquidation_cascade_trigger + spot_price + reserve_ratio | ≥7 weight |

#### Structural Family (2) — NEW
| ID | Pattern | Type | Min Signals | Threshold |
|---|---|---|---|---|
| AP-037 | Metamorphic Contract Attack | B: Multi Tx | create2_redeployment + selfdestruct_detected + drain_ratio | ≥9 weight |
| AP-038 | Multiple Asset Sweep | A: Single Tx | multiple_asset_drain_same_tx + drain_ratio + same_block_deploy | ≥5 weight |

---

## 5. Elasticsearch Mapping Redesign

The `forensics` index mapping must accommodate ALL 35 derived types, 58 signals, and 38 patterns. Fields organized by domain.

### Core Fields (every document)
- investigation_id (keyword), chain_id (integer), @timestamp (date)
- block_number (long), block_datetime (date), tx_hash (keyword)
- layer (keyword): raw | decoded | derived | signal | alert | attacker | case
- derived_type (keyword): one of the 35 derived type names
- source_tx_hash (keyword), source_log_index (integer), source_layer (keyword)

### Address Fields
- from_address (keyword), to_address (keyword)
- caller_address (keyword), callee_address (keyword)
- deployer_address (keyword), contract_address (keyword)
- owner_address (keyword), spender_address (keyword)
- actor_address (keyword), user_address (keyword)
- trader_address (keyword), attacker_wallet (keyword)
- victim_contract (keyword), liquidator_address (keyword)
- borrower_address (keyword), proposer_address (keyword)
- oracle_contract (keyword), pool_address (keyword)
- token_address (keyword), governance_contract (keyword)
- recipient_address (keyword)

### Value Fields
- value_eth (double), value_wei (keyword)
- amount_decimal (double), amount_raw (keyword)
- balance_before_eth (double), balance_after_eth (double)
- delta_eth (double), fee_eth (double)
- total_in_eth (double), total_out_eth (double)
- net_eth (double), drain_ratio (double)
- max_single_hop_eth (double), total_stolen_eth (double)
- funds_drained_eth (double), funding_amount_eth (double)
- received_eth (double), forwarded_eth (double)
- collateral_seized_eth (double), debt_repaid_eth (double)
- amount_in (double), amount_out (double)
- share_price (double), total_assets_eth (double)
- total_supply (double), share_price_delta_pct (double)

### Execution / Trace Fields
- call_type (keyword): CALL | DELEGATECALL | STATICCALL | CREATE | CREATE2 | SELFDESTRUCT
- call_depth (integer), call_index (integer)
- func_selector (keyword), func_name (keyword)
- gas_used (long), gas_limit (long), gas_price_gwei (double)
- success (boolean), has_error (boolean)
- revert_reason (keyword), parent_type (keyword)
- depth_spread (integer), call_count (integer)
- bytecode_size_bytes (integer)

### Event Fields
- event_name (keyword), event_args (flattened)
- function_name (keyword), function_args (flattened)
- log_index (integer), position_in_tx (integer)
- decode_status (keyword): decoded | partial | unknown
- action_type (keyword), new_value (keyword)

### Token Fields
- token_symbol (keyword), token_decimals (integer)
- token_id (keyword), transfer_type (keyword)
- is_infinite (boolean), is_max_approval (boolean)
- token_contract (keyword)

### Storage Fields
- slot_hex (keyword), value_before (keyword), value_after (keyword)
- is_new_slot (boolean), slot_type (keyword)
- updated_before_call (boolean), updated_after_call (boolean)
- updated_between_calls (boolean)

### Signal / Detection Fields
- signal_name (keyword), signal_family (keyword)
- score (float), severity (keyword), confidence (float)
- description (text), evidence_refs (keyword)
- weight (integer)

### Pattern / Alert Fields
- pattern_id (keyword), pattern_name (keyword)
- attack_type (keyword), attack_family (keyword)
- signals_fired (keyword), min_weight_required (integer)
- total_weight_achieved (integer)
- attack_block_range_from (long), attack_block_range_to (long)

### Graph / Attribution Fields
- cluster_id (keyword), cluster_wallets (keyword), cluster_size (integer)
- funded_via (keyword), funding_block (long)
- first_seen_block (long), exploit_block (long)
- hop_number (integer), hop_index (integer)
- direction (keyword), edge_type (keyword)
- taint_score (float), exit_routes (keyword)
- blocks_delta (integer), blocks_since_prev_hop (integer)

### Label Fields
- labels (keyword), ofac_match (boolean), known_exploiter (boolean)
- protocol_name (keyword), is_fresh_wallet (boolean)

### Nonce / Timing Fields
- nonce_before (integer), nonce_after (integer), nonce_delta (integer)
- blocks_before_attack (integer)
- gas_utilisation_pct (double), tx_count (integer)

### Oracle / Price Fields
- price_at_start (double), price_at_end (double), price_delta_pct (double)
- reserve_ratio_before (double), reserve_ratio_after (double)
- oracle_source (keyword), return_value (keyword)

### Permit Fields
- deadline (long), signature_hash (keyword)
- permit_owner (keyword), permit_spender (keyword)

### Governance Fields
- proposal_id (keyword), vote_weight (double)
- voting_period_blocks (integer)

### Case / Context Fields
- case_id (keyword), client_name (keyword), mode (keyword)
- stats (flattened), timeline (flattened), metadata (flattened), raw_extra (flattened)

---

## 6. Simulation Design (3 Attack Scenarios, ~200 Transactions)

### Scenario 1: Reentrancy Drain (existing — enhanced)
- Deploy VulnerableVault
- 20 users deposit (varied amounts, multiple blocks)
- 10 normal withdrawals
- Attacker deploys ReentrancyAttacker in same block as attack
- Recursive drain empties vault
- Attacker splits funds to 3 fresh wallets
- **~60 transactions**
- **Tests:** AP-001 Classic Reentrancy, AP-030 Attacker Deployment, AP-031 Fund Dispersion

### Scenario 2: Flash Loan + Oracle Manipulation (enhanced)
- Deploy LendingPool, SimplePriceOracle, LiquidityPool
- 15 users provide liquidity, 10 users borrow
- Normal price updates (5 oracle txs)
- Attacker flash borrows, swaps to move price, borrows against inflated collateral, repays
- Attacker converts stolen tokens to ETH
- **~80 transactions**
- **Tests:** AP-006 Flash Loan+Oracle, AP-009 AMM Spot Price, signals: flashloan_bracket, spot_price_manipulation, drain_ratio

### Scenario 3: Admin Key Compromise + Drain (enhanced)
- Deploy GovernanceToken with owner, minter roles
- 20 normal mints to users
- Normal transfers between users
- 10 approval transactions
- Attacker takes ownership, mints max supply, dumps on DEX
- Drain all ETH from DEX pair
- **~60 transactions**
- **Tests:** AP-012 Ownership Hijack, AP-020 Mint and Dump, signals: ownership_transfer_then_drain, mint_to_dump_ratio, multiple_asset_drain

### Total: ~200 transactions across 3 scenarios

Each scenario outputs a `client/` folder with ABIs + manifest.json (the client handover). ChainSentinel never sees attacker source code.

---

## 7. Implementation Phases (Build Order)

### Phase 1: Foundation Restructure
- Restructure `derived.py` → `derived/` package with `__init__.py` registry
- Update ES mappings with all new fields
- Update `runner.py` to call derived log registry
- Update `ingest.py` with correct ID generation for all derived types
- Keep existing functionality working

### Phase 2: Core Derived Logs (6 logs)
- contract_deployments, contract_interactions, gas_analysis
- eth_transfers, failed_transactions, enriched_event_logs

### Phase 3: Trace-Dependent Derived Logs (8 logs)
- execution_structure, internal_calls, reentrancy_patterns
- value_flow_intra_tx, state_delta_per_tx, event_sequence
- failed_internals, price_reads

### Phase 4: Behavioural + Graph Derived Logs (14 logs)
- All 8 behavioural + 6 graph logs

### Phase 5: Specialist Derived Logs (7 logs)
- Token, approval, governance, liquidation, permit, donation, share_price

### Phase 6: Detection Signals (58 signals)
- All .esql files, organized by family

### Phase 7: Attack Patterns (38 patterns)
- All .eql files

### Phase 8: Simulations (3 scenarios)
- Enhanced reentrancy, flash loan+oracle, admin key compromise
- ~200 total transactions
- End-to-end testing

### Phase 9: Integration + Frontend Update
- Pipeline runner wired to all derived logs
- Frontend displays new signal/pattern types
- Kibana dashboards for forensic team

---

## 8. Adjustments from Bible Audit

These are the 12 locked adjustments:

1. **Merged** gas_analysis_per_block + gas_analysis_per_tx → gas_analysis
2. **Removed** enriched_block_summary → folded into block_address_activity
3. **Tagged** governance_actions, liquidation_events, share_price_history as specialist
4. **Added** build-order: reentrancy_patterns derives from execution_structure
5. **Added** signal: contract_size_anomaly (W1, Behavioural)
6. **Tagged** Slow Rug pattern as Phase 2 rolling-window engine
7. **Added** signal: same_block_deploy_and_attack (W3, Behavioural)
8. **Added** signal: multiple_asset_drain_same_tx (W2, Value)
9. **Added** signal: create2_redeployment (W3, Structural)
10. **Added** pattern: Metamorphic Contract Attack (AP-037)
11. **Added** derived log: multi_token_balance_snapshot
12. **Added** pattern: Multiple Asset Sweep (AP-038)
13. **Added** caveats: integer_overflow (pre-0.8 only), fee_on_transfer (needs registry), value_concentration (exclude DEX routers)
