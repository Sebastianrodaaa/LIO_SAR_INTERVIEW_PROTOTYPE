"""Follow-up questions against the live graph and the last ICM briefs."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from engine.graphrag import retrieve
from engine.graph_store import GraphStore
from engine.hats import HATS
from init_workspace import PIPELINE


def _covering(store: GraphStore, requester_id: str, amount: float) -> tuple[dict | None, list[dict]]:
    path = store.approval_walk(requester_id, amount)
    skipped: list[dict] = []
    covering = None
    for node in path[1:]:
        if node.get("out_of_office"):
            skipped.append(node)
            continue
        if (node.get("approval_threshold_usd") or 0) >= amount:
            covering = node
            break
    return covering, skipped


def _last_brief(stage: str) -> str:
    path = PIPELINE / stage / "output.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if "awaiting run" in text:
        return ""
    return text


def _resolve_mentioned(store: GraphStore, message: str) -> dict[str, Any] | None:
    lower = message.lower()
    ranked = sorted(
        store.snapshot().nodes,
        key=lambda n: len(str(n.get("name") or n.get("title") or "")),
        reverse=True,
    )
    for node in ranked:
        label = (node.get("name") or node.get("title") or "").lower()
        if len(label) >= 4 and label in lower:
            return node
        nid = (node.get("id") or "").lower()
        if nid and nid in lower:
            return node
    first_names: dict[str, dict[str, Any]] = {}
    for node in ranked:
        if node.get("kind") != "Employee":
            continue
        first = (node.get("name") or "").split(" ")[0].lower()
        if first:
            first_names.setdefault(first, node)
    for first, node in first_names.items():
        if len(first) >= 4 and first in lower:
            return node
    return None


def _describe_node(node: dict[str, Any]) -> str:
    kind = node.get("kind")
    name = node.get("name") or node.get("title") or node.get("id")
    if kind == "Employee":
        ooo = ""
        if node.get("out_of_office"):
            until = node.get("ooo_until") or "they return"
            ooo = f" They are out of office until {until}."
        return (
            f"{name} is {node.get('role')} in {node.get('department')}, "
            f"spender limit ${node.get('approval_threshold_usd') or 0:,.0f}."
            f"{ooo}"
        )
    if kind == "Vendor":
        soc = "holds SOC 2 Type II" if node.get("soc2") else "does not hold SOC 2 Type II"
        notes = f" {node.get('notes')}" if node.get("notes") else ""
        return (
            f"{name} supplies {node.get('category')} — {soc}, "
            f"compliance score {node.get('compliance_score')}."
            f"{' Incumbent.' if node.get('incumbent') else ''}{notes}"
        )
    if kind == "Policy":
        body = (node.get("body") or "").replace("\n", " ").strip()[:280]
        return f"{name} ({node.get('id')}): {body}"
    if kind == "Department":
        return f"{name} is a Northstar team (cost center {node.get('cost_center') or 'n/a'})."
    return f"{name} is on the company graph."


def answer_question(
    store: GraphStore,
    message: str,
    last: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    lower = message.lower()
    requester_id = last.get("requester_id") or "emp-alex-rivera"
    amount = float(last.get("amount_usd") or 15_000)
    vendor_id = last.get("vendor_id") or "vnd-figma"
    mentioned = _resolve_mentioned(store, message)

    stage = (
        "05_approval_routing"
        if any(w in lower for w in ("sign", "approv", "jordan", "ooo", "away", "skip", "route", "who can"))
        else "03_vendor_sourcing"
        if any(w in lower for w in ("penpot", "soc", "adobe", "figma", "vendor"))
        else "02_compliance_check"
        if mentioned and mentioned.get("kind") == "Policy"
        else "01_intake"
    )
    yield {
        "event": "stage_start",
        "stage": stage,
        "index": -1,
        "hat": "Graph lookup",
        "provider": "graph",
        "kind": "ask",
    }

    highlight: list[str] = []
    loaded: list[str] = []
    answer = ""

    if mentioned and (
        "tell me" in lower
        or "about" in lower
        or mentioned.get("kind") in {"Policy", "Department"}
        or not any(w in lower for w in ("sign", "approv", "who can", "skip", "buy"))
    ):
        highlight = [mentioned["id"]]
        loaded = [mentioned.get("name") or mentioned.get("title") or mentioned["id"]]
        answer = _describe_node(mentioned)
        yield {
            "event": "reasoning",
            "kind": "tool",
            "label": "Graph lookup",
            "detail": f"MATCH {mentioned.get('kind')} {mentioned['id']}",
            "highlight": highlight,
        }
    elif any(w in lower for w in ("sign", "approv", "who can", "who has to", "route")):
        covering, skipped = _covering(store, requester_id, amount)
        path = store.approval_walk(requester_id, amount)
        highlight = [n["id"] for n in path]
        loaded = [n.get("name") or n["id"] for n in path]
        skip_names = ", ".join(n.get("name") or n["id"] for n in skipped) or "nobody"
        cover_name = (covering or {}).get("name") or "no one with enough limit"
        cover_limit = (covering or {}).get("approval_threshold_usd")
        answer = (
            f"For ${amount:,.0f}, the reporting walk skips {skip_names} "
            f"(out of office) and stops at {cover_name}"
            + (f" (${cover_limit:,.0f} limit)." if cover_limit else ".")
            + " Nothing is purchased until that person signs."
        )
        yield {
            "event": "reasoning",
            "kind": "tool",
            "label": "GraphRAG retrieve",
            "detail": f"REPORTS_TO walk from {requester_id} until threshold ≥ ${amount:,.0f}",
            "path": None,
            "highlight": highlight,
        }
    elif any(w in lower for w in ("jordan", "ooo", "away", "skip", "out of office")):
        jordan = store.employee("emp-jordan-hale")
        highlight = ["emp-jordan-hale", "pol-ooo-routing", requester_id]
        loaded = ["Jordan Hale", "POL-PPL-009 Out-of-office approval skip"]
        until = (jordan or {}).get("ooo_until") or "until they return"
        answer = (
            f"Jordan Hale is marked out of office ({until}). POL-PPL-009 says skip "
            "OOO approvers — do not wait. The packet walks to the next in-office "
            "manager whose limit covers the amount."
        )
        yield {
            "event": "reasoning",
            "kind": "tool",
            "label": "GraphRAG retrieve",
            "detail": "Employee Jordan Hale + GOVERNS policy POL-PPL-009",
            "highlight": highlight,
        }
    elif any(w in lower for w in ("maya", "limit", "threshold", "helena")):
        name = "Maya Chen" if "helena" not in lower else "Helena Voss"
        emp_id = "emp-helena-voss" if "helena" in lower else "emp-maya-chen"
        emp = store.employee(emp_id)
        highlight = [emp_id]
        loaded = [name]
        answer = (
            f"{emp.get('name')} is {emp.get('role')} with a "
            f"${emp.get('approval_threshold_usd'):,.0f} spender limit."
            if emp
            else f"No employee record for {name}."
        )
        yield {
            "event": "reasoning",
            "kind": "tool",
            "label": "GraphRAG retrieve",
            "detail": f"MATCH employee {emp_id}",
            "highlight": highlight,
        }
    elif any(w in lower for w in ("penpot", "soc 2", "soc2", "adobe", "figma", "miro", "vendor", "eligible")):
        retrieval = retrieve(store, "03_vendor_sourcing", {**last, "amount_usd": amount, "vendor_id": vendor_id})
        highlight = retrieval.get("highlight") or []
        vendors = retrieval.get("vendors") or []
        loaded = [v.get("name") for v in vendors if v.get("name")]
        target = next(
            (v for v in vendors if (v.get("name") or "").lower() in lower),
            next((v for v in vendors if v.get("id") == vendor_id), vendors[0] if vendors else {}),
        )
        soc = "holds SOC 2 Type II" if target.get("soc2") else "does not hold SOC 2 Type II"
        answer = (
            f"{target.get('name')} {soc}. Compliance score {target.get('compliance_score')}. "
            f"{'Preferred incumbent.' if target.get('incumbent') else 'Not the incumbent.'} "
            f"{target.get('notes') or ''}"
        )
        yield {
            "event": "reasoning",
            "kind": "tool",
            "label": "GraphRAG retrieve",
            "detail": retrieval.get("query"),
            "highlight": highlight,
        }
    else:
        brief = _last_brief("05_approval_routing") or _last_brief("01_intake")
        covering, skipped = _covering(store, requester_id, amount)
        highlight = [requester_id]
        if covering:
            highlight.append(covering["id"])
        loaded = ["last output.md"]
        snippet = brief.split("\n\n")[1] if brief else "No brief on disk yet — run a purchase first."
        answer = snippet[:600]
        yield {
            "event": "reasoning",
            "kind": "read",
            "label": "Read last brief on disk",
            "detail": "Follow-up uses the file the last hat wrote, not a new giant prompt.",
            "path": "workspace/pipeline/",
            "highlight": highlight,
        }

    yield {
        "event": "reasoning",
        "kind": "skip",
        "label": "Left on disk (not in this prompt)",
        "detail": "Only the slice needed to answer this question. Sister hats were not reloaded.",
        "highlight": highlight,
    }
    yield {
        "event": "thought_delta",
        "kind": "thought",
        "text": answer.strip(),
        "content": answer.strip(),
        "highlight": highlight,
    }
    yield {
        "event": "answer",
        "content": answer.strip(),
        "highlight": highlight,
        "loaded": loaded,
        "hat": "Graph lookup",
    }
    yield {"event": "ask_complete", "highlight": highlight}


def hat_caption(stage: str, amount: float | None = None) -> str:
    cap = HATS.get(stage, {}).get("caption", "")
    if amount and stage == "05_approval_routing":
        return cap.replace("the amount", f"${amount:,.0f}")
    return cap
