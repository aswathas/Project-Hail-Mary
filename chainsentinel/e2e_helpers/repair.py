"""Diagnose validation failures and propose fixes."""
from elasticsearch import Elasticsearch
from e2e_helpers.validator import Validator


class Repair:
    def __init__(self, es_host: str = "localhost:9200"):
        self.es = Elasticsearch([f"http://{es_host}"])
        self.validator = Validator(es_host)

    def diagnose(self, failed_checks: dict) -> dict:
        """Diagnose why checks failed."""
        diagnosis = {}

        if not failed_checks.get("tx_count", {}).get("passed"):
            try:
                health = self.es.cluster.health()
                if health["status"] != "green":
                    diagnosis["issue"] = "Elasticsearch not healthy"
                    diagnosis["fix"] = "Restart ES: docker-compose down && docker-compose up"
            except Exception as e:
                diagnosis["issue"] = f"ES connection failed: {e}"
                diagnosis["fix"] = "Check ES is running on localhost:9200"

        if not failed_checks.get("decoded_logs", {}).get("passed"):
            try:
                indices = self.es.indices.get_alias(index="forensics")
                if "forensics" not in indices:
                    diagnosis["issue"] = "forensics index doesn't exist"
                    diagnosis["fix"] = "Run: python -m chainsentinel.es.setup"
                else:
                    diagnosis["issue"] = "Decoded logs not present — decoder may have failed"
                    diagnosis["fix"] = "Check pipeline logs for decoder errors"
            except Exception as e:
                diagnosis["issue"] = f"Cannot check indices: {e}"
                diagnosis["fix"] = "Check ES health and permissions"

        if not failed_checks.get("signals", {}).get("passed"):
            diagnosis["issue"] = "No signals in forensics index"
            diagnosis["fix"] = "Verify signal_engine ran: check server logs"

        if not diagnosis:
            diagnosis["issue"] = "Unknown failure"
            diagnosis["fix"] = "Check ES and pipeline logs manually"

        return diagnosis

    def suggest_fix(self, diagnosis: dict) -> str:
        """Suggest fix command."""
        return diagnosis.get("fix", "Manual investigation required")
