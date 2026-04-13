"""
Report Template — builds structured JSON context from ES data.

Queries ES for all investigation data (signals, alerts, attacker profiles,
fund trails, timeline events) and assembles a structured context object
that gets passed to the LLM for report generation.
"""
import json
from typing import Optional


def _query_layer(es_client, investigation_id: str, layer: str, size: int = 500) -> list[dict]:
    """Query ES for documents of a specific layer."""
    response = es_client.search(
        index="forensics",
        query={
            "bool": {
                "must": [
                    {"term": {"investigation_id": investigation_id}},
                    {"term": {"layer": layer}},
                ]
            }
        },
        size=size,
        sort=[{"block_number": "asc"}] if layer != "attacker" else [{"@timestamp": "desc"}],
    )
    return [hit["_source"] for hit in response.get("hits", {}).get("hits", [])]


def build_report_context(
    es_client,
    investigation_id: str,
    chain_id: int,
) -> dict:
    """
    Build a structured context object from all investigation data in ES.

    Returns dict with keys:
        case_id, chain_id, signals, alerts, attacker_profile,
        fund_trail, timeline, stats
    """
    signals = _query_layer(es_client, investigation_id, "signal")
    alerts = _query_layer(es_client, investigation_id, "alert")
    attacker_docs = _query_layer(es_client, investigation_id, "attacker")
    derived = _query_layer(es_client, investigation_id, "derived", size=1000)

    # Extract attacker profile (first profile doc)
    attacker_profile = None
    fund_trail_docs = []
    for doc in attacker_docs:
        if doc.get("attacker_type") == "profile" and attacker_profile is None:
            attacker_profile = doc
        elif doc.get("attacker_type") == "fund_trail":
            fund_trail_docs.append(doc)

    # Build timeline from signals + derived events
    timeline = []
    for sig in signals:
        timeline.append({
            "block_number": sig.get("block_number"),
            "type": "signal",
            "name": sig.get("signal_name"),
            "severity": sig.get("severity"),
            "description": sig.get("description"),
            "tx_hash": sig.get("tx_hash"),
        })
    for d in derived:
        if d.get("derived_type") in ("native_transfer", "asset_transfer", "admin_action"):
            timeline.append({
                "block_number": d.get("block_number"),
                "type": "derived",
                "name": d.get("derived_type"),
                "description": f"{d.get('from_address', '?')} -> {d.get('to_address', '?')}: {d.get('value_eth', 0)} ETH",
                "tx_hash": d.get("tx_hash"),
            })

    timeline.sort(key=lambda x: x.get("block_number") or 0)

    # Compute stats
    all_blocks = set()
    all_txs = set()
    for doc in signals + derived:
        if doc.get("block_number"):
            all_blocks.add(doc["block_number"])
        if doc.get("tx_hash"):
            all_txs.add(doc["tx_hash"])

    stats = {
        "signal_count": len(signals),
        "alert_count": len(alerts),
        "block_count": len(all_blocks),
        "tx_count": len(all_txs),
    }

    return {
        "case_id": investigation_id,
        "chain_id": chain_id,
        "signals": signals,
        "alerts": alerts,
        "attacker_profile": attacker_profile,
        "fund_trail": fund_trail_docs,
        "timeline": timeline,
        "stats": stats,
    }


def format_context_as_prompt(ctx: dict) -> str:
    """
    Format the structured context into a text prompt for the LLM.
    Keeps it concise but includes all forensic evidence.
    """
    lines = []
    lines.append(f"# Investigation: {ctx['case_id']}")
    lines.append(f"Chain ID: {ctx['chain_id']}")
    lines.append("")

    # Stats
    s = ctx["stats"]
    lines.append(f"## Statistics")
    lines.append(f"- Signals fired: {s['signal_count']}")
    lines.append(f"- Attack patterns matched: {s['alert_count']}")
    lines.append(f"- Blocks analyzed: {s['block_count']}")
    lines.append(f"- Transactions analyzed: {s['tx_count']}")
    lines.append("")

    # Alerts
    if ctx["alerts"]:
        lines.append("## Attack Patterns Detected")
        for alert in ctx["alerts"]:
            lines.append(f"- **{alert.get('pattern_name', 'Unknown')}** (confidence: {alert.get('confidence', 0)})")
            lines.append(f"  Attacker: {alert.get('attacker_wallet', 'Unknown')}")
            lines.append(f"  Victim: {alert.get('victim_contract', 'Unknown')}")
            lines.append(f"  Funds drained: {alert.get('funds_drained_eth', 0)} ETH")
            lines.append(f"  Signals: {', '.join(alert.get('signals_fired', []))}")
        lines.append("")

    # Signals
    if ctx["signals"]:
        lines.append("## Signals Fired")
        for sig in ctx["signals"]:
            lines.append(f"- [{sig.get('severity', 'MED')}] **{sig.get('signal_name', '')}** "
                        f"(score: {sig.get('score', 0)}) — {sig.get('description', '')}")
        lines.append("")

    # Attacker profile
    if ctx["attacker_profile"]:
        ap = ctx["attacker_profile"]
        lines.append("## Attacker Profile")
        lines.append(f"- Wallets: {', '.join(ap.get('cluster_wallets', []))}")
        lines.append(f"- Total stolen: {ap.get('total_stolen_eth', 0)} ETH")
        lines.append(f"- Fund trail hops: {ap.get('fund_trail_hops', 0)}")
        lines.append(f"- Exit routes: {', '.join(ap.get('exit_routes', []))}")
        lines.append("")

    # Timeline (abbreviated)
    if ctx["timeline"]:
        lines.append("## Timeline")
        for event in ctx["timeline"][:20]:  # Cap at 20 for prompt size
            sev = f"[{event.get('severity', '')}] " if event.get("severity") else ""
            lines.append(f"- Block {event.get('block_number', '?')}: "
                        f"{sev}{event.get('name', '')} — {event.get('description', '')}")
        if len(ctx["timeline"]) > 20:
            lines.append(f"  ... and {len(ctx['timeline']) - 20} more events")
        lines.append("")

    return "\n".join(lines)
