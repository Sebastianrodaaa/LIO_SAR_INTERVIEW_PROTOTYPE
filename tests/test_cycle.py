"""Smoke-test the offline cycle: five validated artifacts, OOO skip."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.graph_store import NetworkXStore
from engine.llm import StructuredLLM
from engine.orchestrator import ProcurementOrchestrator
from init_workspace import PIPELINE, STAGES, init_workspace
from mock_data_generator import generate


def test_offline_cycle(tmp_path_factory=None) -> None:
    generate()
    init_workspace(reset_outputs=True)
    store = NetworkXStore()
    store.seed()
    orch = ProcurementOrchestrator(store, StructuredLLM())
    request = {
        "request_id": "PR-2026-0847",
        "requester_id": "emp-alex-rivera",
        "vendor_id": "vnd-figma",
        "item": "Figma Enterprise",
        "vendor_hint": "Figma",
        "category": "design-tools",
        "amount_usd": 15_000,
        "seats": 120,
        "justification": "SCIM required.",
        "urgency": "high",
    }
    events = list(orch.run(request, gated=False, stage_pause_s=0))
    written = [e for e in events if e["event"] == "file_written"]
    assert len(written) == 5
    for stage in STAGES:
        text = (PIPELINE / stage / "output.md").read_text(encoding="utf-8")
        assert "awaiting run" not in text
    approval = Path(PIPELINE / "05_approval_routing" / "output.md").read_text(encoding="utf-8")
    assert "Maya Chen" in approval
    assert "skipped" in approval.lower() or "OOO" in approval
    thought = " ".join(
        str(e.get("content") or "") for e in events if e["event"] == "thought_delta"
    )
    assert "Alex Rivera" in thought
    assert "Jordan Hale" in thought
    assert "Maya Chen" in thought
    walk = store.approval_walk("emp-alex-rivera", 15_000)
    assert walk[1]["name"] == "Jordan Hale"
    assert walk[1]["out_of_office"] is True
    assert walk[2]["name"] == "Maya Chen"


def test_gated_pauses_each_stage() -> None:
    generate()
    init_workspace(reset_outputs=True)
    store = NetworkXStore()
    store.seed()
    orch = ProcurementOrchestrator(store, StructuredLLM())
    request = {
        "request_id": "PR-2026-0847",
        "requester_id": "emp-alex-rivera",
        "vendor_id": "vnd-figma",
        "item": "Figma Enterprise",
        "vendor_hint": "Figma",
        "category": "design-tools",
        "amount_usd": 15_000,
        "seats": 120,
        "justification": "SCIM required.",
        "urgency": "high",
    }
    first = list(orch.run(request, gated=True, stage_pause_s=0))
    written = [e for e in first if e["event"] == "file_written"]
    assert len(written) == 1
    assert written[0]["stage"] == "01_intake"
    assert any(e["event"] == "awaiting_human" and e.get("next_stage") == "02_compliance_check" for e in first)
    assert "awaiting run" in (PIPELINE / "02_compliance_check" / "output.md").read_text(encoding="utf-8")

    second = list(orch.run_from(request, "02_compliance_check", gated=True))
    written2 = [e for e in second if e["event"] == "file_written"]
    assert len(written2) == 1
    assert written2[0]["stage"] == "02_compliance_check"
    assert any(e["event"] == "awaiting_human" for e in second)
    assert "awaiting run" in (PIPELINE / "03_vendor_sourcing" / "output.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    test_offline_cycle()
    test_gated_pauses_each_stage()
    print("offline cycle ok")
