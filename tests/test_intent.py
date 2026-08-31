"""Intent parser and amount-sensitive routing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.graph_store import NetworkXStore
from engine.intent import parse_amount, parse_message
from engine.llm import StructuredLLM
from engine.orchestrator import ProcurementOrchestrator
from init_workspace import PIPELINE, init_workspace
from mock_data_generator import generate


def test_parse_amount() -> None:
    assert parse_amount("$15,000 Figma") == 15000
    assert parse_amount("what if it were 4900") == 4900
    assert parse_amount("make it 60k") == 60000


def test_parse_penpot_and_ask() -> None:
    run = parse_message("Buy Penpot instead of Figma for 120 seats.")
    assert run["kind"] == "run"
    assert run["request"]["vendor_id"] == "vnd-penpot"
    ask = parse_message("Tell me about Maya Chen.", last=run["request"])
    assert ask["kind"] == "ask"
    why = parse_message("Why skip Jordan?", last=run["request"])
    assert why["kind"] == "ask"


def test_amount_changes_approver() -> None:
    generate()
    init_workspace(reset_outputs=True)
    store = NetworkXStore()
    store.seed()
    orch = ProcurementOrchestrator(store, StructuredLLM())
    sixty = {
        "request_id": "PR-TEST-60K",
        "requester_id": "emp-alex-rivera",
        "vendor_id": "vnd-figma",
        "item": "Figma Enterprise",
        "vendor_hint": "Figma",
        "category": "design-tools",
        "amount_usd": 60_000,
        "seats": 120,
        "justification": "what if 60k",
        "urgency": "high",
    }
    events = list(orch.run(sixty, gated=False, stage_pause_s=0))
    written = [e for e in events if e["event"] == "file_written"]
    thought = " ".join(
        str(e.get("content") or e.get("text") or "")
        for e in events
        if e["event"] == "thought_delta"
    )
    assert "Alex Rivera" in thought
    assert "Jordan Hale" in thought and "away" in thought.lower()
    assert "Helena Voss" in thought
    assert any(e["event"] == "delta" for e in events)
    approval = next(e for e in written if e["stage"] == "05_approval_routing")
    assert approval["json"]["spender_approver_name"] == "Helena Voss"
    assert "Helena" in (approval.get("summary") or "")
    text = (PIPELINE / "05_approval_routing" / "output.md").read_text(encoding="utf-8")
    assert "Helena Voss" in text
    assert "60,000" in text or "60000" in text


def test_thoughts_follow_vendor_and_amount() -> None:
    generate()
    init_workspace(reset_outputs=True)
    store = NetworkXStore()
    store.seed()
    orch = ProcurementOrchestrator(store, StructuredLLM())
    penpot = {
        "request_id": "PR-TEST-PENPOT",
        "requester_id": "emp-alex-rivera",
        "vendor_id": "vnd-penpot",
        "item": "Penpot",
        "vendor_hint": "Penpot",
        "category": "design-tools",
        "amount_usd": 4_900,
        "seats": 120,
        "justification": "Buy Penpot for 4900",
        "urgency": "high",
    }
    events = list(orch.run(penpot, gated=False, stage_pause_s=0))
    thought = " ".join(
        str(e.get("content") or "") for e in events if e["event"] == "thought_delta"
    )
    assert "Penpot" in thought
    assert "fails eligibility" in thought or "does not hold SOC 2" in thought
    assert "under the $10,000" in thought
    from engine.ask import answer_question

    asked = list(answer_question(store, "Tell me about Maya Chen.", penpot))
    blob = " ".join(str(e.get("content") or "") for e in asked if e["event"] in {"thought_delta", "answer"})
    assert "Maya Chen" in blob
    assert "50,000" in blob or "50000" in blob


if __name__ == "__main__":
    test_parse_amount()
    test_parse_penpot_and_ask()
    test_amount_changes_approver()
    test_thoughts_follow_vendor_and_amount()
    print("intent ok")
