# ChainSentinel — PowerPoint / Presentation Prompt

## How to Use This
Paste the prompt below into any AI presentation tool:
- **Gamma.app** (best for Lamborghini-style dark premium slides)
- **Beautiful.ai**
- **Canva AI**
- **ChatGPT → export to PowerPoint**
- **Claude → give to a designer**

---

## THE PROMPT (copy everything below this line)

---

Create a premium, ultra-high-end presentation for a blockchain forensics tool called **ChainSentinel**, built by **SISA Information Security**. The style should be **dark luxury** — think Lamborghini, Rolex, Black AMEX. Dark backgrounds (#0A0A0F), electric accent colors (neon green #00FF88 for success/detection, electric blue #00BFFF for data flow, amber #FFB800 for warnings, crimson #FF2D55 for threats). High contrast white typography. Minimal text per slide. Bold visual data storytelling.

Font: Use a geometric sans-serif (Orbitron, Space Grotesk, or Inter). Headings should be large (60-80pt), body text small (14-16pt max per bullet).

The presentation should be **18 slides** with this exact structure:

---

**SLIDE 1 — TITLE SLIDE**
Background: Deep black with a subtle hex grid overlay and one bright green pulse node.
Title: CHAINSENTINEL (large, bold, letter-spaced)
Subtitle: "Blockchain Forensics Intelligence Platform"
Below: SISA Information Security | 2026
Right side: A glowing green circuit-board chain visualization

---

**SLIDE 2 — THE PROBLEM (HOOK)**
Headline: "DeFi Lost $2.7 Billion to Smart Contract Exploits in 2024"
Visual: Dark red bar chart showing exploit losses by category (reentrancy, flash loans, oracle manipulation, admin key abuse)
Three stats in large glowing boxes:
- 4.7 min average time to exploit completion
- 180 days average time to post-mortem
- 0 tools purpose-built for EVM forensics at forensic-grade evidence quality
Bottom: "Forensic investigation shouldn't start after the money is gone."

---

**SLIDE 3 — THE CLIENT SCENARIO**
Headline: "A Client Calls SISA at 2AM"
Dark dramatic visual (alarm clock, red glow)
Three column layout:
LEFT (red): "They provide: RPC endpoint | Contract ABIs | Block range | 'We were exploited'"
CENTER (arrow animation): CHAINSENTINEL
RIGHT (green): "We find: Attack transaction | Attacker wallet | Fund trail | Attack pattern | 5-second alert"

---

**SLIDE 4 — WHAT CHAINSENTINEL IS**
Headline: "One Tool. Full Chain. From Raw Data to Attribution."
Four capability cards (dark glass-morphism style):
1. COLLECT — Pulls every block, tx, log, internal trace from any EVM node
2. DECODE — Understands 400+ smart contract function signatures automatically
3. DETECT — 61 signals + 20 attack patterns running in Elasticsearch
4. ATTRIBUTE — Traces funds 5 hops, clusters wallets, flags mixers and CEX deposits

---

**SLIDE 5 — THE PIPELINE (ARCHITECTURE)**
Full-width dark diagram with left-to-right flow:

RPC NODE → [COLLECTOR] → forensics-raw → [NORMALIZER] → [DECODER] → forensics/decoded → [DERIVED ENGINE] → forensics/derived → [SIGNAL ENGINE 61 ES|QL] → forensics/signals → [PATTERN ENGINE 20 EQL] → ALERT → [CORRELATION BFS] → ATTRIBUTION

Use glowing nodes in neon green. Arrows in electric blue.
Caption: "Python is plumbing. Elasticsearch is the brain."

---

**SLIDE 6 — THREE ANALYSIS MODES**
Headline: "Three Threat Entry Points"
Three large dark cards with icons:

🔍 TX MODE
"I have one suspicious transaction hash"
→ deepest analysis, full trace, sub-second result

📦 RANGE MODE  
"I know the attack time window"
→ batch processing, block by block, full pipeline on all transactions

👁 WALLET HUNT
"I have a suspicious wallet address"
→ 5-hop BFS fund tracing, attacker profiling, cluster mapping

---

**SLIDE 7 — LAYER 1: DATA COLLECTION**
Headline: "We Read Everything the Chain Knows"
Left side: Code-style dark terminal showing JSON output (block, tx, receipt, trace)
Right side: Three method names with explanations:
- eth_getLogs → every event emitted
- eth_getTransactionReceipt → success/fail, gas, logs
- debug_traceTransaction → internal call tree (the secret weapon)
Footer: "Full trace support on Anvil and archive nodes. Graceful degradation on basic RPC."

---

**SLIDE 8 — LAYER 2: THE ABI DECODER**
Headline: "Every Byte of Calldata Gets Decoded"
Visual: A lock opening, with hex bytes transforming into readable function calls
Priority waterfall (top to bottom):
1. Client ABIs (provided at engagement start) 
2. ERC20 / ERC721 / ERC1155 standards
3. Uniswap V2/V3, Aave, Compound, Curve
4. 4-byte selector cache (grows every investigation)
Show before/after:
BEFORE: 0x3ccfd60b00000000000000000000000000000000000000000000000002c68af0bb140000
AFTER: withdraw(amount=200000000000000000)

---

**SLIDE 9 — LAYER 3: 9 SECURITY PRIMITIVES**
Headline: "9 Derived Event Types. Every Attack Signature."
Dark grid of 9 cells, each with an icon and name:
- value_flow_intra_tx (lightning bolt)
- price_reads (eye icon)
- access_control (shield)
- deployment (rocket)
- liquidity_change (waves)
- token_transfer (arrow exchange)
- governance_action (gavel)
- call_depth (nested brackets)
- storage_pattern (database with clock)

Caption: "These are the security building blocks every signal is built on."

---

**SLIDE 10 — LAYER 4: 61 SIGNALS**
Headline: "61 Signals. 12 Threat Families."
Radial/donut chart showing signal families:
- Value (7), Flash Loan (3), Access (5), Deployment (3), Liquidity (2)
- Token (4), Governance (3), DeFi (6), Structural (10), Behavioural (7)
- Bridge (2), Graph (4), Evasion (3)
Each segment in a different neon shade.
Right side: Example signal card — "recursive_depth_pattern: Transaction reaches call depth ≥3 with recursive pattern → Reentrancy indicator"
Caption: "Adding a signal = drop one .esql file. No code changes. No redeployment."

---

**SLIDE 11 — LAYER 5: PATTERN ENGINE (THE CORRELATOR)**
Headline: "Attacks Aren't One Event. They're a Choreography."
Dark cinematic layout showing three signals becoming one alert:
[recursive_depth_pattern] ──┐
[storage_update_delay]    ──┼──► AP-001 REENTRANCY ALERT (95% confidence)
[value_drain_per_depth]   ──┘     Block 33 | Tx: 0x76d28f...

Text: "EQL sequence queries correlate signals across time. One match = confirmed attack."

---

**SLIDE 12 — LIVE DEMO: REENTRANCY ATTACK**
Headline: "Reentrancy Attack — Detected in Real Time"
Timeline visualization:
Block 1-32: Normal vault deposits (green dots)
Block 33: RED EXPLOSION — Attack transaction
         "recursive_depth_pattern ✓"
         "storage_update_delay ✓"
         "value_drain_per_depth ✓"
         "→ AP-001 ALERT: 95% confidence"
Block 34+: Cover traffic (grey dots)

Right panel: Alert card (dark red border, white text):
ATTACK DETECTED
Pattern: classic_reentrancy
Confidence: 95%
Transaction: 0x76d28f...
Block: 33
Signals: 3/3 matched

---

**SLIDE 13 — FUND TRACE & ATTRIBUTION**
Headline: "Follow the Money. 5 Hops."
Graph visualization (dark background, glowing nodes):
ATTACKER (red) → fresh1 (orange) → Tornado Cash (yellow/flagged)
                → fresh2 (orange) → CEX Deposit (labelled)
Taint scores shown on edges: 1.0 → 0.7 → 0.49
OFAC label badge shown on sanctioned wallet
Caption: "BFS traversal, haircut taint scoring, labeled known entities: mixers, bridges, CEX wallets, OFAC SDN list."

---

**SLIDE 14 — KIBANA DASHBOARD**
Headline: "Real-Time Intelligence. Not Spreadsheets."
Full-width screenshot placeholder (dark dashboard):
- Signal timeline chart (line chart, 206 signals over time)
- Alert count tile (1 alert fired)
- Top signals bar chart
- Investigation status panel
Caption: "Every investigation automatically populates a Kibana forensics dashboard."

---

**SLIDE 15 — AI COPILOT (OLLAMA)**
Headline: "Ask Questions. Get Forensic Answers."
Chat UI mockup (dark terminal style):
Q: "What happened in this transaction?"
A: "Transaction 0x76d28f... is a classic single-function reentrancy attack. 
    The attacker's contract called VulnerableVault.withdraw() at block 33. 
    The vault sent 0.1 ETH before updating its internal balance state, 
    allowing the attacker to re-enter and drain 0.3 ETH total 
    across 3 recursive calls. Three detection signals fired, 
    triggering a 95% confidence AP-001 alert."

Caption: "Ollama (Gemma 3 1B, local) — never sends investigation data to external APIs."

---

**SLIDE 16 — DEPLOYMENT FLEXIBILITY**
Headline: "One Tool. Three Environments."
Three-column dark card layout:
🏠 LOCAL ANVIL → Full traces | Zero cost | Development & training
🧪 SEPOLIA TESTNET → Real network | Client pre-production testing
🌐 MAINNET → Production investigations | Archive node | Full coverage

"Switching environments = changing 2 lines in config.json"
Code snippet: { "rpc_url": "...", "chain_id": 1 }

---

**SLIDE 17 — WHY CHAINSENTINEL vs OTHERS**
Headline: "Built for Forensics. Not Monitoring."
Comparison table (dark glass):
Feature | ChainSentinel | Existing Tools
Evidence-grade raw index | ✅ | ❌
Client ABI intake | ✅ | ❌
61 ES|QL signals | ✅ | ❌ (rule-based)
EQL sequence patterns | ✅ | ❌
Fund trace + attribution | ✅ | Partial
Offline / local operation | ✅ | ❌ (cloud-only)
AI forensic report | ✅ | ❌
Open signal library | ✅ | ❌ (vendor-locked)

---

**SLIDE 18 — CLOSING SLIDE**
Large, cinematic, minimal.
Background: Electric dark with glowing green pulse network
Headline: "Every Attack Leaves a Trail on Chain."
Subheadline: "ChainSentinel finds it."
Bottom: SISA Information Security | chainsentinel.sisa.in | 2026
One call-to-action: "Request a Demo"

---

END OF PROMPT

---

## Design Notes for Designers

- All charts should use dark background (#0A0A0F or #0D0D1A)
- Accent: neon green #00FF88 for confirmed detections, safe states
- Accent: electric blue #00BFFF for data flows, pipeline arrows
- Accent: amber #FFB800 for signals, warnings
- Accent: crimson #FF2D55 for alerts, attacks, threat indicators
- White #FFFFFF for main text, #999999 for secondary text
- Cards: glass morphism (rgba(255,255,255,0.05) background, 1px border rgba(255,255,255,0.1))
- Avoid gradients unless subtle (dark → slightly less dark)
- Include SISA logo (top-left corner on every slide after slide 1)
- All code/transaction hashes: monospace font (JetBrains Mono or Fira Code)
