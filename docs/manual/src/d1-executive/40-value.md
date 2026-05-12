# 4. Value to SISA

ChainSentinel changes three things about how SISA delivers blockchain
forensics engagements.

## 4.1 Time to first verdict drops by an order of magnitude

The demos show 5–15 minutes from data to a client-ready report. For
real engagements the bottleneck shifts from analyst hand-work to RPC
throughput and clients' ABI handover speed — both addressable.

## 4.2 Consistency improves because the rules are machine-readable

Two analysts running ChainSentinel against the same data get the same
signals and patterns. Differences come from *judgement on top of* the
analysis, not from the analysis itself.

## 4.3 Detection coverage scales with the SISA team's knowledge

Because every detection rule is an `.esql` or `.eql` file — not Python
code — adding a new detection is a Pull Request that any team member
who knows Elasticsearch can write. As SISA accumulates engagement
experience, the rule base grows.

## 4.4 No data leaves the engagement

- LLM runs locally on the analyst's machine.
- Elasticsearch runs locally.
- The only thing that ever talks to the public internet is the RPC
  endpoint, which the client chooses (Alchemy, Infura, their own
  archive node).

This matters for sensitive engagements where the client cannot
authorise sending data to OpenAI, Anthropic, Chainalysis, or any
SaaS forensics tool.

## 4.5 Offline-demonstrable

The full demo runs on a laptop, on a plane, without internet. Foundry
simulations on Anvil reproduce real engagement workflows so SISA can
walk a prospective client through the tool without exposing past
clients' data.

## 4.6 Open architecture

Every architectural decision (see **D3 §9 ADRs**) optimises for
modularity. New chains, new patterns, new derived events, new ABIs
are *additive* — there are no schema migrations, no rule-engine
rewrites, no compiled binaries to redistribute.
