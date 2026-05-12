# 8. Family: graph (6 signals)

Graph signals look at **wallet relationships** — funding lineage, mixer
or bridge interactions, multi-hop trails, address clusters. They are
the bridge between detection and correlation.

| Stem | File | Inputs |
|------|------|--------|
| `address_cluster_identified` | `detection/signals/graph/address_cluster_identified.esql` | `correlation.clustering` output |
| `bridge_interaction_detected` | `detection/signals/graph/bridge_interaction_detected.esql` | `derived/eth_transfers`, `label_db` |
| `contract_creator_linked` | `detection/signals/graph/contract_creator_linked.esql` | `derived/contract_creator_graph` |
| `fund_dispersion_post_attack` | `detection/signals/graph/fund_dispersion_post_attack.esql` | `derived/fund_hop_chains` |
| `mixer_interaction_detected` | `detection/signals/graph/mixer_interaction_detected.esql` | `derived/eth_transfers`, `label_db` |
| `multi_hop_fund_trail` | `detection/signals/graph/multi_hop_fund_trail.esql` | `derived/fund_hop_chains` |

## 8.1 Per-signal notes

### `mixer_interaction_detected`
- **Score weight:** `0.85`
- **Detection:** Any address in the investigation interacted (incoming
  or outgoing) with a known mixer contract from `label_db`.
- **FP notes:** Privacy-conscious legitimate users mix funds; this is a
  *graph context* signal, not a verdict.

### `bridge_interaction_detected`
- **Score weight:** `0.7`
- **Detection:** Address interacted with a known bridge contract.
- **FP notes:** Routine cross-chain liquidity moves match constantly;
  used as a graph predicate for `AP-033`.

### `multi_hop_fund_trail`
- **Score weight:** `0.6`
- **Detection:** A path of length ≥ 3 from the victim to a known mixer /
  bridge / CEX through previously unrelated EOAs.
- **FP notes:** Some retail users naturally go victim → CEX → home
  wallet → DEX.

### `fund_dispersion_post_attack`
- **Score weight:** `0.8`
- **Detection:** The attacker EOA's outflow branching factor exceeds 5
  within 50 blocks of the exploit transaction.
- **FP notes:** Distribution scripts and faucets match.

### `address_cluster_identified`
- **Score weight:** `0.75`
- **Detection:** The clustering subsystem grouped two or more addresses
  with shared funding / creator / timing properties.
- **FP notes:** Tightly-coupled multisig signers cluster legitimately.

### `contract_creator_linked`
- **Score weight:** `0.65`
- **Detection:** The victim contract's creator EOA is also the
  attacker — or one hop away from the attacker via the creator graph.
- **FP notes:** Self-administered protocols inherently match.
