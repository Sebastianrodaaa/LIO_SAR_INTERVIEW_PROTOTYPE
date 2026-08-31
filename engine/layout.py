"""Cockpit layout for the seed graph.

Positions are authored, not force-directed, so the live demo never jitters.
The orchestrator only sends highlight ids; the frontend animates from here.
"""

from __future__ import annotations

from typing import Any

from engine.graph_store import GraphSnapshot

# Coordinates in a 960×620 viewBox.
LAYOUT: dict[str, tuple[float, float]] = {
    "emp-helena-voss": (480, 36),
    "emp-maya-chen": (300, 130),
    "emp-jordan-hale": (300, 230),
    "emp-alex-rivera": (300, 340),
    "emp-dana-foster": (660, 130),
    "dept-engineering": (120, 230),
    "dept-legal": (120, 420),
    "dept-itsec": (120, 500),
    "pol-spend-10k": (820, 300),
    "pol-soc2": (820, 380),
    "pol-ooo-routing": (820, 220),
    "pol-sso": (820, 460),
    "pol-legal-dpa": (820, 540),
    "vnd-figma": (520, 430),
    "vnd-adobe": (640, 500),
    "vnd-sketch": (400, 500),
    "vnd-penpot": (520, 540),
    "vnd-miro": (640, 430),
    "cat-design-tools": (520, 360),
}


VISIBLE_KINDS = {"Employee", "Department", "Vendor", "Policy"}
FOCUS_IDS = set(LAYOUT.keys())


def cockpit_graph(snapshot: GraphSnapshot, highlight: list[str] | None = None) -> dict[str, Any]:
    highlight_set = set(highlight or [])
    nodes = []
    for node in snapshot.nodes:
        if node.get("id") not in FOCUS_IDS:
            continue
        if node.get("kind") not in VISIBLE_KINDS:
            continue
        x, y = LAYOUT[node["id"]]
        nodes.append(
            {
                "id": node["id"],
                "kind": node.get("kind"),
                "label": node.get("name") or node.get("title") or node["id"],
                "subtitle": _subtitle(node),
                "ooo": bool(node.get("out_of_office")),
                "x": x,
                "y": y,
                "active": node["id"] in highlight_set,
                "facts": _facts(node),
            }
        )

    node_ids = {n["id"] for n in nodes}
    edges = []
    for edge in snapshot.edges:
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            continue
        edges.append(
            {
                "source": edge["source"],
                "target": edge["target"],
                "kind": edge.get("kind"),
                "active": edge["source"] in highlight_set and edge["target"] in highlight_set,
            }
        )

    return {
        "backend": snapshot.backend,
        "nodes": nodes,
        "edges": edges,
        "highlight": list(highlight_set),
    }


def _facts(node: dict[str, Any]) -> dict[str, Any]:
    kind = node.get("kind")
    if kind == "Employee":
        return {
            "role": node.get("role"),
            "department": node.get("department"),
            "threshold_usd": node.get("approval_threshold_usd"),
            "ooo_until": node.get("ooo_until"),
            "email": node.get("email"),
            "location": node.get("location"),
        }
    if kind == "Vendor":
        return {
            "category": node.get("category"),
            "score": node.get("compliance_score"),
            "soc2": node.get("soc2"),
            "incumbent": node.get("incumbent"),
            "sla": node.get("sla"),
            "notes": node.get("notes"),
        }
    if kind == "Policy":
        body = (node.get("body") or "").replace("\n", " ").strip()
        return {
            "policy_id": node.get("id"),
            "threshold_usd": node.get("threshold_usd"),
            "body": body[:320],
        }
    if kind == "Department":
        return {"cost_center": node.get("cost_center")}
    return {}


def _subtitle(node: dict[str, Any]) -> str:
    kind = node.get("kind")
    if kind == "Employee":
        extra = " · OOO" if node.get("out_of_office") else ""
        threshold = node.get("approval_threshold_usd")
        if threshold is not None:
            return f"{node.get('role', '')} · ${threshold:,.0f}{extra}"
        return (node.get("role") or "") + extra
    if kind == "Vendor":
        return f"{node.get('category')} · score {node.get('compliance_score')}"
    if kind == "Policy":
        return node.get("id", "")
    if kind == "Department":
        return node.get("cost_center") or ""
    return ""
