#!/usr/bin/env python3
"""Seed the property graph from ./data.

Schema
------
Nodes: Employee, Department, Vendor, Policy  (+ Category helper)
Edges: REPORTS_TO, BELONGS_TO, SUPPLIES, GOVERNS

Seed scenario
-------------
Alex Rivera (Junior SWE, $500) requests $15,000 Figma Enterprise.
Jordan Hale (manager, $5k) is OOO, so the approval walk continues to
Maya Chen (VP Engineering, $50k). The orchestrator computes that path
from the graph — it is not hard-coded in a prompt.
"""

from __future__ import annotations

import json
from pathlib import Path

from engine.graph_store import connect_store
from engine.layout import cockpit_graph

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "data" / "graph_snapshot.json"


def seed() -> None:
    store = connect_store()
    store.seed()
    snap = store.snapshot()
    view = cockpit_graph(snap, highlight=["emp-alex-rivera", "emp-jordan-hale", "emp-maya-chen", "vnd-figma"])
    SNAPSHOT.write_text(
        json.dumps(
            {
                "backend": snap.backend,
                "node_count": len(snap.nodes),
                "edge_count": len(snap.edges),
                "cockpit": view,
                "scenario": snap.meta.get("seed"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    path = store.approval_walk("emp-alex-rivera", 15_000)
    names = " → ".join(
        f"{n['name']}{' (OOO)' if n.get('out_of_office') else ''}"
        for n in path
    )
    print(f"Seeded {snap.backend}: {len(snap.nodes)} nodes, {len(snap.edges)} edges")
    print(f"Approval walk: {names}")
    print(f"Wrote {SNAPSHOT}")


if __name__ == "__main__":
    seed()
