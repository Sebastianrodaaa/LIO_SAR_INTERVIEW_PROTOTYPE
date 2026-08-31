"""Stage-scoped GraphRAG.

Each function returns a compact bundle the orchestrator injects into *that
stage only*. This is select+isolate from context-engineering practice, and
the reason a $15k Figma request does not pull Datadog's SLA into the
compliance prompt.
"""

from __future__ import annotations

from typing import Any

from engine.graph_store import GraphStore


def _compact_employee(emp: dict[str, Any] | None) -> dict[str, Any] | None:
    if not emp:
        return None
    return {
        "id": emp.get("id"),
        "name": emp.get("name"),
        "role": emp.get("role"),
        "department": emp.get("department"),
        "manager_id": emp.get("manager_id"),
        "out_of_office": emp.get("out_of_office"),
        "ooo_until": emp.get("ooo_until"),
        "approval_threshold_usd": emp.get("approval_threshold_usd"),
    }


def _compact_vendor(vendor: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": vendor.get("id"),
        "name": vendor.get("name"),
        "category": vendor.get("category"),
        "compliance_score": vendor.get("compliance_score"),
        "preferred": vendor.get("preferred"),
        "incumbent": vendor.get("incumbent"),
        "soc2": vendor.get("soc2"),
        "iso27001": vendor.get("iso27001"),
        "gdpr_dpa": vendor.get("gdpr_dpa"),
        "sla": vendor.get("sla"),
        "existing_contract": vendor.get("existing_contract"),
        "pricing_tiers": vendor.get("pricing_tiers"),
        "notes": vendor.get("notes"),
    }


def retrieve(store: GraphStore, stage: str, request: dict[str, Any]) -> dict[str, Any]:
    requester_id = request["requester_id"]
    vendor_id = request.get("vendor_id")
    amount = float(request["amount_usd"])
    category = request.get("category", "design-tools")
    requester = store.employee(requester_id)
    department = (requester or {}).get("department", "Engineering")

    if stage == "01_intake":
        manager = store.employee((requester or {}).get("manager_id") or "")
        team = store.neighborhood(requester_id, depth=1)
        highlight = [requester_id]
        if manager:
            highlight.append(manager["id"])
        return {
            "query": f"MATCH requester {requester_id} plus manager and department",
            "highlight": highlight,
            "requester": _compact_employee(requester),
            "manager": _compact_employee(manager),
            "department": department,
            "team_size": len(team.get("nodes", [])),
        }

    if stage == "02_compliance_check":
        policies = store.policies_for(department, category, amount)
        return {
            "query": f"GOVERNS {department} AND threshold <= {amount} AND category {category}",
            "highlight": [p["id"] for p in policies] + ["dept-engineering", "dept-legal", "dept-itsec"],
            "policies": [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "threshold_usd": p.get("threshold_usd"),
                    "body": p.get("body"),
                    "filename": p.get("filename"),
                }
                for p in policies
            ],
            "amount_usd": amount,
            "category": category,
            "seats": request.get("seats", 0),
        }

    if stage == "03_vendor_sourcing":
        vendors = [_compact_vendor(v) for v in store.vendors_in_category(category)]
        hinted = _compact_vendor(store.vendor(vendor_id) or {}) if vendor_id else None
        return {
            "query": f"SUPPLIES {category} ORDER BY preferred, compliance_score",
            "highlight": [v["id"] for v in vendors],
            "category": category,
            "vendors": vendors,
            "hinted_vendor": hinted,
        }

    if stage == "04_negotiation_strategy":
        primary_id = request.get("primary_vendor_id") or vendor_id
        vendor = _compact_vendor(store.vendor(primary_id) or {}) if primary_id else None
        return {
            "query": f"Vendor {primary_id} tiers, SLA, contract",
            "highlight": [primary_id] if primary_id else [],
            "vendor": vendor,
            "amount_usd": amount,
        }

    if stage == "05_approval_routing":
        path = store.approval_walk(requester_id, amount)
        covering = None
        skipped = []
        for node in path[1:]:  # skip requester
            if node.get("out_of_office"):
                skipped.append(node["id"])
                continue
            if (node.get("approval_threshold_usd") or 0) >= amount:
                covering = node
                break
        highlight = [n["id"] for n in path]
        return {
            "query": f"REPORTS_TO walk from {requester_id} skip OOO until threshold >= {amount}",
            "highlight": highlight,
            "path": [_compact_employee(n) for n in path],
            "skipped_ooo": skipped,
            "covering_approver": _compact_employee(covering),
            "amount_usd": amount,
            "functional_reviewers_hint": [
                "Nina Patel — IT SecReview",
                "Sophie Laurent — Legal DPA",
                "Mei Lin — Procurement copy",
            ],
        }

    return {"query": "none", "highlight": []}
