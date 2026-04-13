"""Validate ES ingestion: check counts for txs, derived, signals, patterns."""
from elasticsearch import Elasticsearch


class Validator:
    def __init__(self, es_host: str = "localhost:9200"):
        self.es = Elasticsearch([f"http://{es_host}"])

    def validate_all(self, investigation_ids: list[str]) -> dict:
        """Run all validations and return summary."""
        results = {
            "investigations": investigation_ids,
            "checks": {},
            "passed": True,
        }

        # Check 1: forensics-raw (transaction documents)
        tx_count = self.es.count(
            index="forensics-raw",
            query={"bool": {"filter": [{"term": {"doc_type": "transaction"}}]}}
        )["count"]
        results["checks"]["tx_count"] = {
            "expected_min": 200,
            "actual": tx_count,
            "passed": tx_count >= 200,
        }
        if not results["checks"]["tx_count"]["passed"]:
            results["passed"] = False

        # Check 2: forensics decoded logs
        decoded_count = self.es.count(
            index="forensics",
            query={"bool": {"filter": [{"term": {"layer": "decoded"}}]}}
        )["count"]
        results["checks"]["decoded_logs"] = {
            "expected_min": 200,
            "actual": decoded_count,
            "passed": decoded_count >= 200,
        }
        if not results["checks"]["decoded_logs"]["passed"]:
            results["passed"] = False

        # Check 3: derived events (all 35 types)
        derived = self.es.search(
            index="forensics",
            size=0,
            aggs={"derived_types": {"terms": {"field": "derived_type", "size": 100}}}
        )
        derived_type_count = len(derived["aggregations"]["derived_types"]["buckets"])
        results["checks"]["derived_types"] = {
            "expected_min": 30,
            "actual": derived_type_count,
            "passed": derived_type_count >= 30,
        }
        if not results["checks"]["derived_types"]["passed"]:
            results["passed"] = False

        # Check 4: signals
        signal_count = self.es.count(
            index="forensics",
            query={"bool": {"filter": [{"term": {"layer": "signal"}}]}}
        )["count"]
        results["checks"]["signals"] = {
            "expected_min": 100,
            "actual": signal_count,
            "passed": signal_count >= 100,
        }
        if not results["checks"]["signals"]["passed"]:
            results["passed"] = False

        # Check 5: patterns/alerts
        alert_count = self.es.count(
            index="forensics",
            query={"bool": {"filter": [{"term": {"layer": "alert"}}]}}
        )["count"]
        results["checks"]["alerts"] = {
            "expected_min": 10,
            "actual": alert_count,
            "passed": alert_count >= 10,
        }
        if not results["checks"]["alerts"]["passed"]:
            results["passed"] = False

        return results

    def print_summary(self, results: dict):
        """Print human-readable summary."""
        status = "✓ PASS" if results["passed"] else "✗ FAIL"
        print(f"\n{status} — E2E Validation Summary")
        print("=" * 60)
        for check_name, check_data in results["checks"].items():
            status_sym = "✓" if check_data["passed"] else "✗"
            print(
                f"{status_sym} {check_name:20} {check_data['actual']:6d} / {check_data['expected_min']:6d}"
            )
        print("=" * 60)
