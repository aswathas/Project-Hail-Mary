#!/usr/bin/env python3
"""
ChainSentinel Kibana Setup — Kibana 8.x compatible
Creates data views and a dashboard using only lnsMetric + lnsDatatable panels.
"""
import json
import time
import urllib.request
import urllib.error

import os
KIBANA_URL = os.environ.get("KIBANA_URL", "http://localhost:5601")
HEADERS = {"Content-Type": "application/json", "kbn-xsrf": "true"}


def kibana_request(method: str, path: str, body=None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{KIBANA_URL}{path}", data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        content = e.read().decode()
        if e.code == 409:
            return {"status": "already_exists"}
        raise RuntimeError(f"Kibana {method} {path} → {e.code}: {content[:400]}") from e


def wait_for_kibana(max_wait: int = 120) -> None:
    print("Waiting for Kibana...")
    for i in range(max_wait // 5):
        try:
            req = urllib.request.Request(f"{KIBANA_URL}/api/status", headers={"kbn-xsrf": "true"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                s = json.loads(resp.read())
                if s.get("status", {}).get("overall", {}).get("level") == "available":
                    print("  Kibana ready")
                    return
        except Exception:
            pass
        print(f"  Waiting... ({(i+1)*5}s)")
        time.sleep(5)
    raise TimeoutError("Kibana not ready")


def create_data_view(index_pattern: str, name: str) -> str:
    print(f"  Creating data view: {name} ({index_pattern})")
    result = kibana_request("POST", "/api/data_views/data_view", {
        "data_view": {"title": index_pattern, "name": name, "timeFieldName": "@timestamp"},
        "override": True,
    })
    dv_id = result.get("data_view", {}).get("id", "unknown")
    print(f"    id: {dv_id}")
    return dv_id


def _metric_panel(uid: str, title: str, dv_id: str, x: int, y: int, w: int, h: int,
                  kuery: str = "") -> dict:
    """KPI metric — count of documents, optionally filtered by KQL."""
    col: dict = {
        "label": title,
        "dataType": "number",
        "operationType": "count",
        "isBucketed": False,
        "scale": "ratio",
        "sourceField": "___records___",
    }
    if kuery:
        col["filter"] = {"language": "kuery", "query": kuery}

    return {
        "type": "lens",
        "panelIndex": uid,
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": uid},
        "version": "8.12.0",
        "embeddableConfig": {
            "attributes": {
                "title": "",
                "description": "",
                "visualizationType": "lnsMetric",
                "type": "lens",
                "references": [{"id": dv_id, "name": "indexpattern-datasource-layer-l1", "type": "index-pattern"}],
                "state": {
                    "visualization": {
                        "layerId": "l1",
                        "layerType": "data",
                        "metricAccessor": "m1",
                    },
                    "query": {"query": "", "language": "kuery"},
                    "filters": [],
                    "internalReferences": [],
                    "adHocDataViews": {},
                    "datasourceStates": {
                        "formBased": {
                            "layers": {
                                "l1": {
                                    "columnOrder": ["m1"],
                                    "columns": {"m1": col},
                                    "incompleteColumns": {},
                                }
                            }
                        }
                    },
                },
            },
            "enhancements": {},
            "title": title,
            "hidePanelTitles": False,
        },
    }


def _table_panel(uid: str, title: str, dv_id: str, x: int, y: int, w: int, h: int,
                 kuery: str, bucket_field: str, bucket_label: str) -> dict:
    """Datatable — top values of a field with count, filtered by KQL."""
    return {
        "type": "lens",
        "panelIndex": uid,
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": uid},
        "version": "8.12.0",
        "embeddableConfig": {
            "attributes": {
                "title": "",
                "description": "",
                "visualizationType": "lnsDatatable",
                "type": "lens",
                "references": [{"id": dv_id, "name": "indexpattern-datasource-layer-l1", "type": "index-pattern"}],
                "state": {
                    "visualization": {
                        "layerId": "l1",
                        "layerType": "data",
                        "columns": [
                            {"columnId": "b1", "isTransposed": False},
                            {"columnId": "m1", "isTransposed": False},
                        ],
                    },
                    "query": {"query": kuery, "language": "kuery"},
                    "filters": [],
                    "internalReferences": [],
                    "adHocDataViews": {},
                    "datasourceStates": {
                        "formBased": {
                            "layers": {
                                "l1": {
                                    "columnOrder": ["b1", "m1"],
                                    "columns": {
                                        "b1": {
                                            "label": bucket_label,
                                            "dataType": "string",
                                            "operationType": "terms",
                                            "isBucketed": True,
                                            "scale": "ordinal",
                                            "sourceField": bucket_field,
                                            "params": {
                                                "size": 20,
                                                "orderBy": {"type": "column", "columnId": "m1"},
                                                "orderDirection": "desc",
                                                "missingBucket": False,
                                                "otherBucket": False,
                                            },
                                        },
                                        "m1": {
                                            "label": "Count",
                                            "dataType": "number",
                                            "operationType": "count",
                                            "isBucketed": False,
                                            "scale": "ratio",
                                            "sourceField": "___records___",
                                        },
                                    },
                                    "incompleteColumns": {},
                                }
                            }
                        }
                    },
                },
            },
            "enhancements": {},
            "title": title,
            "hidePanelTitles": False,
        },
    }


def delete_old_dashboards() -> None:
    try:
        result = kibana_request(
            "GET",
            "/api/saved_objects/_find?type=dashboard&search=ChainSentinel&search_fields=title&per_page=20"
        )
        for obj in result.get("saved_objects", []):
            kibana_request("DELETE", f"/api/saved_objects/dashboard/{obj['id']}")
            print(f"  Deleted: {obj['attributes']['title']}")
    except Exception:
        pass


def create_dashboard(f_dv: str, raw_dv: str) -> str:
    print("  Building dashboard panels...")

    panels = [
        # ── Row 1: KPI Metrics ── y=0, h=5
        _metric_panel("p01", "Total Forensic Docs",     f_dv,  0,  0, 12, 5),
        _metric_panel("p02", "Signals Detected",        f_dv, 12,  0, 12, 5, "layer: signal"),
        _metric_panel("p03", "Derived Security Events", f_dv, 24,  0, 12, 5, "layer: derived"),
        _metric_panel("p04", "Attack Alerts",           f_dv, 36,  0, 12, 5, "layer: alert"),

        # ── Row 2: Raw evidence KPIs ── y=5, h=5
        _metric_panel("p05", "Raw Transactions",        raw_dv,  0, 5, 12, 5),
        _metric_panel("p06", "Raw Logs",                raw_dv, 12, 5, 12, 5),
        _metric_panel("p07", "Decoded Events",          f_dv,   24, 5, 12, 5, "layer: decoded"),
        _metric_panel("p08", "Attacker Profiles",       f_dv,   36, 5, 12, 5, "layer: attacker"),

        # ── Row 3: Signals table ── y=10, h=14
        _table_panel("p09", "Signals by Name",
                     f_dv, 0, 10, 24, 14,
                     "layer: signal", "signal_name", "Signal"),
        _table_panel("p10", "Signal Families",
                     f_dv, 24, 10, 24, 14,
                     "layer: signal", "signal_family", "Family"),

        # ── Row 4: Derived events + Alerts ── y=24, h=14
        _table_panel("p11", "Derived Event Types",
                     f_dv, 0, 24, 24, 14,
                     "layer: derived", "derived_type", "Derived Type"),
        _table_panel("p12", "Attack Alerts (Pattern ID)",
                     f_dv, 24, 24, 24, 14,
                     "layer: alert", "pattern_id", "Pattern"),

        # ── Row 5: Top senders/receivers ── y=38, h=14
        _table_panel("p13", "Top Attacker Wallets (from_address)",
                     f_dv, 0, 38, 24, 14,
                     "layer: signal", "from_address", "Address"),
        _table_panel("p14", "Top Victim Contracts (to_address)",
                     f_dv, 24, 38, 24, 14,
                     "layer: signal", "to_address", "Contract"),
    ]

    result = kibana_request("POST", "/api/saved_objects/dashboard", {
        "attributes": {
            "title": "ChainSentinel — Forensics Overview",
            "description": "EVM blockchain forensics: signals, alerts, derived events",
            "panelsJSON": json.dumps(panels),
            "timeRestore": False,
            "optionsJSON": json.dumps({
                "useMargins": True,
                "syncColors": False,
                "hidePanelTitles": False,
            }),
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "query": {"query": "", "language": "kuery"},
                    "filter": [],
                })
            },
        }
    })
    dashboard_id = result.get("id", "unknown")
    print(f"  Dashboard id: {dashboard_id}")
    return dashboard_id


def main():
    print("=" * 60)
    print("ChainSentinel Kibana Setup")
    print("=" * 60)

    wait_for_kibana()

    print("\n[1/3] Removing old dashboards...")
    delete_old_dashboards()

    print("\n[2/3] Creating data views...")
    f_dv  = create_data_view("forensics",     "ChainSentinel — Forensics")
    raw_dv = create_data_view("forensics-raw", "ChainSentinel — Raw Evidence")

    print("\n[3/3] Creating dashboard...")
    did = create_dashboard(f_dv, raw_dv)

    print("\n" + "=" * 60)
    print("Done!")
    print(f"\n  Dashboard:  http://localhost:5601/app/dashboards#/view/{did}")
    print(f"  Discover:   http://localhost:5601/app/discover")
    print()
    print("  ── Finding SIGNALS in Kibana ──────────────────────────")
    print("  Discover → select 'ChainSentinel — Forensics'")
    print("  Search:  layer: signal")
    print("  Columns to add: signal_name, score, severity, tx_hash, block_number")
    print()
    print("  ── Finding ALERTS in Kibana ───────────────────────────")
    print("  Discover → same data view")
    print("  Search:  layer: alert")
    print("  Columns: pattern_id, pattern_name, confidence, signals_fired")
    print()
    print("  ── ES|QL in Dev Tools ─────────────────────────────────")
    print('  FROM forensics | WHERE layer == "signal"')
    print('    | STATS count = COUNT(*) BY signal_name | SORT count DESC')
    print()
    print('  FROM forensics | WHERE layer == "alert"')
    print('    | KEEP pattern_id, pattern_name, confidence, tx_hash, block_number')
    print("=" * 60)


if __name__ == "__main__":
    main()
