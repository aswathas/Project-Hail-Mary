"""Governance Actions — detects on-chain governance events."""
from pipeline.derived._base import base_doc

GOVERNANCE_EVENTS = {
    "ProposalCreated",
    "VoteCast",
    "ProposalExecuted",
    "ProposalCanceled",
    "Canceled",
}


async def derive(raw_data: dict, investigation_id: str, config: dict) -> list[dict]:
    """Derive governance_actions records from decoded governance events.

    raw_data keys: normalized_tx, decoded_events
    """
    results = []
    decoded_events = raw_data.get("decoded_events", [])

    for event in decoded_events:
        event_name = event.get("event_name", "")
        if event_name not in GOVERNANCE_EVENTS:
            continue

        args = event.get("event_args", {})
        tx_hash = event.get("tx_hash", "")
        block_number = event.get("block_number", 0)
        block_datetime = event.get("block_datetime", "")
        log_index = event.get("log_index", 0)

        # Normalize action type
        action_map = {
            "ProposalCreated": "proposal_created",
            "VoteCast": "vote_cast",
            "ProposalExecuted": "proposal_executed",
            "ProposalCanceled": "proposal_canceled",
            "Canceled": "proposal_canceled",
        }

        proposal_id = args.get("proposalId", args.get("id", ""))
        proposer = str(args.get("proposer", args.get("voter", ""))).lower()

        doc = base_doc(tx_hash, block_number, block_datetime,
                       investigation_id, "governance_actions", log_index)
        doc.update({
            "governance_contract": event.get("log_address", ""),
            "action_type": action_map.get(event_name, event_name.lower()),
            "proposal_id": str(proposal_id),
            "proposer_address": proposer,
        })
        results.append(doc)

    return results
