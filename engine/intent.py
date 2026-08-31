"""Turn a chat message into a procurement request or a graph question.

The cockpit sends the user's words. This module is the only place that
decides whether to run the ICM loop or answer from the graph.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.graph_store import DATA, GraphStore

ROOT = Path(__file__).resolve().parent.parent

RUN_CUES = (
    "buy",
    "purchase",
    "request",
    "need",
    "review",
    "order",
    "procure",
    "get me",
    "walk",
    "what if",
    "instead",
    "change",
    "make it",
)

ASK_CUES = (
    "why",
    "who",
    "how",
    "does ",
    "do we",
    "is ",
    "can ",
    "what's",
    "what is",
    "what’s",
    "explain",
    "tell me",
)


def _load_catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    employees = json.loads((DATA / "employees.json").read_text(encoding="utf-8"))
    vendors = json.loads((DATA / "vendors.json").read_text(encoding="utf-8"))
    return employees, vendors


def parse_amount(text: str) -> float | None:
    dollar = re.search(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k\b)?", text, re.I)
    if dollar:
        value = float(dollar.group(1).replace(",", ""))
        if dollar.group(2):
            value *= 1000
        return value
    kform = re.search(r"\b(\d+(?:\.\d+)?)\s*k\b", text, re.I)
    if kform:
        return float(kform.group(1)) * 1000
    bare = re.search(r"\b(\d{1,3},\d{3}|\d{4,6})(?:\.\d+)?\b", text)
    if bare:
        return float(bare.group(1).replace(",", ""))
    return None


def parse_seats(text: str) -> int | None:
    match = re.search(r"(\d+)\s*seats?\b", text, re.I)
    return int(match.group(1)) if match else None


def _match_vendor(text: str, vendors: list[dict[str, Any]]) -> dict[str, Any] | None:
    lower = text.lower()
    ranked = sorted(vendors, key=lambda v: len(v.get("name") or ""), reverse=True)
    for vendor in ranked:
        name = (vendor.get("name") or "").lower()
        if len(name) >= 3 and name in lower:
            return vendor
    aliases = {
        "figma": "vnd-figma",
        "adobe": "vnd-adobe",
        "penpot": "vnd-penpot",
        "miro": "vnd-miro",
        "sketch": "vnd-sketch",
        "datadog": "vnd-datadog",
        "aws": "vnd-aws",
        "slack": "vnd-slack",
    }
    for alias, vid in aliases.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            return next((v for v in vendors if v["id"] == vid), None)
    return None


def _match_requester(text: str, employees: list[dict[str, Any]]) -> dict[str, Any] | None:
    lower = text.lower()
    patterns = (
        r"(?:i(?:'m| am)|for|from)\s+([a-z]+(?:\s+[a-z]+)?)",
        r"([a-z]+(?:\s+[a-z]+)?)\s+(?:needs|wants|requested|asks|is requesting)",
    )
    candidates: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            candidates.append(match.group(1).strip())
    ranked = sorted(employees, key=lambda e: len(e.get("name") or ""), reverse=True)
    for employee in ranked:
        name = (employee.get("name") or "").lower()
        if any(name == c or name.startswith(c + " ") or c == name.split()[0] for c in candidates):
            return employee
    return None


def _default_request() -> dict[str, Any]:
    return {
        "requester_id": "emp-alex-rivera",
        "vendor_id": "vnd-figma",
        "item": "Figma Enterprise",
        "vendor_hint": "Figma",
        "category": "design-tools",
        "amount_usd": 15_000,
        "seats": 120,
        "justification": "",
        "urgency": "high",
        "request_id": "PR-2026-0847",
    }


def looks_like_run(text: str) -> bool:
    lower = text.lower()
    if parse_amount(text) is not None:
        return True
    if any(cue in lower for cue in RUN_CUES):
        return True
    return False


def looks_like_ask(text: str) -> bool:
    lower = text.lower().strip()
    if lower.endswith("?"):
        return True
    return any(lower.startswith(cue) or f" {cue}" in f" {lower}" for cue in ASK_CUES)


def parse_message(
    text: str,
    store: GraphStore | None = None,
    last: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return {kind: run|ask, request, notes}."""
    employees, vendors = _load_catalog()
    stripped = text.strip()
    last = dict(last or {})
    last.pop("gated", None)

    want_run = looks_like_run(stripped)
    want_ask = looks_like_ask(stripped)
    if want_ask and not want_run and last.get("requester_id"):
        return {"kind": "ask", "request": last, "message": stripped}

    base = dict(_default_request())
    if last.get("requester_id") and ( "what if" in stripped.lower() or "instead" in stripped.lower()):
        base.update({k: v for k, v in last.items() if v is not None})

    amount = parse_amount(stripped)
    seats = parse_seats(stripped)
    vendor = _match_vendor(stripped, vendors)
    requester = _match_requester(stripped, employees)

    if amount is not None:
        base["amount_usd"] = amount
    if seats is not None:
        base["seats"] = seats
    if vendor:
        base["vendor_id"] = vendor["id"]
        base["vendor_hint"] = vendor["name"]
        base["category"] = vendor.get("category") or base.get("category")
        tier = "Enterprise" if re.search(r"enterprise", stripped, re.I) else ""
        base["item"] = f"{vendor['name']} {tier}".strip()
        if amount is None:
            tiers = vendor.get("pricing_tiers") or []
            picked = None
            need = int(base.get("seats") or 0)
            for t in tiers:
                if t.get("seats", 0) >= need:
                    picked = t
                    break
            if picked:
                base["amount_usd"] = float(picked.get("annual_usd") or base["amount_usd"])
                if picked.get("name"):
                    base["item"] = f"{vendor['name']} {picked['name']}"
    if requester:
        base["requester_id"] = requester["id"]

    if store:
        emp = store.employee(base["requester_id"])
        if emp:
            base.setdefault("requester_name", emp.get("name"))

    stamp = datetime.now(timezone.utc).strftime("%H%M")
    base["request_id"] = f"PR-2026-{stamp}"
    base["justification"] = stripped
    base["urgency"] = "high"
    return {"kind": "run", "request": base, "message": stripped}
