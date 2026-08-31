"""Reasoning beats grounded in *this* GraphRAG slice.

Nothing here is a fixed script. Sentences are assembled from the requester,
policies, vendors, and REPORTS_TO walk returned for the current request.
Change the amount or vendor and the prose changes.
"""

from __future__ import annotations

from typing import Any


def _usd(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _ooo(node: dict[str, Any]) -> str:
    if not node.get("out_of_office"):
        return "in office"
    until = node.get("ooo_until")
    return f"away until {until}" if until else "away"


def thought_beats(
    stage: str,
    request: dict[str, Any],
    retrieval: dict[str, Any],
) -> list[dict[str, Any]]:
    amount = request.get("amount_usd")
    item = request.get("item") or request.get("vendor_hint") or "this purchase"
    seats = int(request.get("seats") or retrieval.get("seats") or 0)
    beats: list[dict[str, Any]] = []

    if stage == "01_intake":
        req = retrieval.get("requester") or {}
        mgr = retrieval.get("manager") or {}
        req_id = req.get("id")
        if req:
            beats.append(
                _beat(
                    f"{req.get('name')} is a {req.get('role')} in {req.get('department')} "
                    f"with a personal approval limit of {_usd(req.get('approval_threshold_usd'))}.",
                    [req_id],
                )
            )
        if mgr:
            beats.append(
                _beat(
                    f"Their manager is {mgr.get('name')} ({mgr.get('role')}, "
                    f"limit {_usd(mgr.get('approval_threshold_usd'))}) — currently {_ooo(mgr)}.",
                    [req_id, mgr.get("id")],
                )
            )
        beats.append(
            _beat(
                f"The chat asks for {item} at {_usd(amount)} across {seats} seats.",
                [req_id],
            )
        )
        threshold = float(req.get("approval_threshold_usd") or 0)
        if amount is not None and float(amount) > threshold:
            beats.append(
                _beat(
                    f"{_usd(amount)} is above {req.get('name')}'s {_usd(threshold)}, "
                    "so this cannot be self-approved — routing has to walk the reporting line later.",
                    [req_id, mgr.get("id")],
                )
            )
        elif amount is not None:
            beats.append(
                _beat(
                    f"{_usd(amount)} sits inside {req.get('name')}'s own limit, "
                    "but Northstar still records the packet before anyone signs.",
                    [req_id],
                )
            )
        return beats

    if stage == "02_compliance_check":
        policies = retrieval.get("policies") or []
        query = retrieval.get("query") or ""
        beats.append(
            _beat(
                f"GraphRAG on this hat is {query or 'GOVERNS for this department, category, and amount'} — "
                f"{len(policies)} matching rule{'s' if len(policies) != 1 else ''}.",
                [p.get("id") for p in policies if p.get("id")],
            )
        )
        for policy in policies:
            title = policy.get("title") or policy.get("id")
            pid = policy.get("id")
            body = (policy.get("body") or "").replace("\n", " ").strip()
            snippet = _clause(body)
            thresh = policy.get("threshold_usd")
            if thresh and amount is not None and float(amount) > float(thresh):
                why = f"it gates spend above {_usd(thresh)} and this request is {_usd(amount)}"
            elif "sso" in (title or "").lower() or "scim" in (title or "").lower():
                why = f"the request has {seats} seats (the gate is 25)"
            elif "soc" in (title or "").lower():
                why = "any vendor that will see Northstar designs or source must hold SOC 2 Type II"
            elif "office" in (title or "").lower() or "ooo" in (pid or "").lower():
                why = "the would-be approver can be marked out of office"
            else:
                why = "it governs this department and category"
            extra = f" {snippet}" if snippet else ""
            beats.append(_beat(f"{pid} ({title}) applies because {why}.{extra}", [pid]))
        if not policies:
            beats.append(_beat("The GOVERNS slice came back empty — no policy in this band.", []))
        if amount is not None and float(amount) < 10_000:
            beats.append(
                _beat(
                    f"Committed value {_usd(amount)} is under the $10,000 software-spend bar, "
                    "so Legal/IT are not forced by POL-FIN-014 on amount alone.",
                    [],
                )
            )
        return beats

    if stage == "03_vendor_sourcing":
        vendors = retrieval.get("vendors") or []
        hinted = retrieval.get("hinted_vendor") or {}
        query = retrieval.get("query") or "SUPPLIES this category"
        beats.append(
            _beat(
                f"Sourcing slice: {query}. {len(vendors)} in-category options on the graph.",
                [v.get("id") for v in vendors if v.get("id")],
            )
        )
        if hinted.get("name"):
            soc = "holds SOC 2 Type II" if hinted.get("soc2") else "does not hold SOC 2 Type II"
            beats.append(
                _beat(
                    f"The requester named {hinted.get('name')} — {soc}, "
                    f"compliance score {hinted.get('compliance_score')}.",
                    [hinted.get("id")],
                )
            )
        for vendor in vendors:
            tiers = vendor.get("pricing_tiers") or []
            chosen = next((t for t in tiers if int(t.get("seats") or 0) >= seats), tiers[-1] if tiers else {})
            eligible = bool(vendor.get("soc2")) and (vendor.get("compliance_score") or 0) >= 75
            if eligible:
                verdict = (
                    f"clears the SOC 2 bar (score {vendor.get('compliance_score')}); "
                    f"{chosen.get('name', 'listed tier')} is {_usd(chosen.get('annual_usd'))} for {chosen.get('seats', seats)} seats"
                )
            else:
                verdict = (
                    f"fails eligibility — SOC 2={'yes' if vendor.get('soc2') else 'no'}, "
                    f"score {vendor.get('compliance_score')} (need 75 and Type II)"
                )
            extra = "; this is the incumbent" if vendor.get("incumbent") else ""
            beats.append(
                _beat(
                    f"{vendor.get('name')}: {verdict}{extra}.",
                    [vendor.get("id")],
                )
            )
        return beats

    if stage == "04_negotiation_strategy":
        vendor = retrieval.get("vendor") or {}
        tiers = vendor.get("pricing_tiers") or []
        vid = vendor.get("id")
        if vendor:
            beats.append(
                _beat(
                    f"Commercial node is {vendor.get('name')}: existing contract "
                    f"{vendor.get('existing_contract') or 'none'}, SLA {vendor.get('sla') or 'n/a'}.",
                    [vid],
                )
            )
        for tier in tiers:
            beats.append(
                _beat(
                    f"List price on {tier.get('name')}: {_usd(tier.get('annual_usd'))} "
                    f"for {tier.get('seats', 0)} seats.",
                    [vid],
                )
            )
        if not tiers:
            beats.append(_beat("No pricing tiers on this vendor node.", [vid] if vid else []))
        return beats

    if stage == "05_approval_routing":
        path = retrieval.get("path") or []
        covering = retrieval.get("covering_approver") or {}
        covering_id = covering.get("id")
        covering_idx = next((i for i, n in enumerate(path) if n.get("id") == covering_id), -1)
        beats.append(
            _beat(
                retrieval.get("query")
                or f"REPORTS_TO walk from {request.get('requester_id')} until an in-office limit covers {_usd(amount)}.",
                [n.get("id") for n in path if n.get("id")],
            )
        )
        for index, node in enumerate(path):
            nid = node.get("id")
            name = node.get("name")
            role = node.get("role")
            limit = _usd(node.get("approval_threshold_usd"))
            ids = [p.get("id") for p in path[: index + 1] if p.get("id")]
            if index == 0:
                beats.append(_beat(f"Start at {name}, {role}, own limit {limit}.", ids))
            elif node.get("out_of_office"):
                beats.append(
                    _beat(
                        f"{name} would be next ({role}, {limit}) but they are {_ooo(node)} — "
                        "POL-PPL-009 says skip, do not wait.",
                        ids + ["pol-ooo-routing"],
                    )
                )
            elif nid == covering_id:
                beats.append(
                    _beat(
                        f"{name} is in office with {limit}, which covers {_usd(amount)}. Stop the walk here.",
                        ids,
                    )
                )
            elif covering_idx >= 0 and index > covering_idx:
                beats.append(
                    _beat(
                        f"{name} sits above {covering.get('name')} ({limit}) and is not asked to sign this amount.",
                        ids,
                    )
                )
            else:
                beats.append(
                    _beat(
                        f"{name}'s {limit} does not cover {_usd(amount)} — keep walking.",
                        ids,
                    )
                )
        if covering:
            beats.append(
                _beat(
                    f"Spender approver is {covering.get('name')} — first in-office manager whose limit covers {_usd(amount)}.",
                    [n.get("id") for n in path if n.get("id")],
                )
            )
        else:
            beats.append(_beat("No one on the reporting line has a limit that covers this amount.", []))
        return beats

    return [_beat(retrieval.get("query") or "Retrieve the stage-scoped graph slice.", [])]


def conclusion_beats(stage: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    beats: list[dict[str, Any]] = []
    if stage == "01_intake" and payload.get("requester_name"):
        ooo = " Manager is out of office." if payload.get("manager_out_of_office") else ""
        beats.append(
            _beat(
                f"Packet: {payload.get('requester_name')} wants {payload.get('item')} "
                f"for {_usd(payload.get('amount_usd'))}.{ooo}",
                [payload.get("requester_id")],
            )
        )
        return beats

    if stage == "02_compliance_check":
        for finding in payload.get("findings") or []:
            beats.append(
                _beat(
                    f"{finding.get('policy_id')} → {finding.get('status')}: "
                    f"{finding.get('requirement') or finding.get('title') or ''}",
                    [],
                )
            )
        for condition in payload.get("conditions") or []:
            beats.append(_beat(str(condition), []))
        return beats

    if stage == "03_vendor_sourcing":
        primary = payload.get("primary_vendor_name")
        if primary:
            alt = payload.get("alternative_vendor_name")
            beats.append(
                _beat(
                    f"Recommend {primary} ({payload.get('primary_tier')}, "
                    f"{_usd(payload.get('primary_annual_usd'))})"
                    + (f", with {alt} as the documented alternative." if alt else "."),
                    [payload.get("primary_vendor_id")],
                )
            )
        return beats

    if stage == "04_negotiation_strategy":
        if payload.get("ask_price_usd"):
            beats.append(
                _beat(
                    f"Ask {_usd(payload.get('ask_price_usd'))} against list "
                    f"{_usd(payload.get('list_price_usd'))} on a {payload.get('term_months')}-month term.",
                    [payload.get("vendor_id")],
                )
            )
        if payload.get("walk_away"):
            beats.append(_beat(f"Walk-away: {payload['walk_away']}", []))
        return beats

    if stage == "05_approval_routing" and payload.get("spender_approver_name"):
        skipped = payload.get("skipped") or []
        skip_txt = ", ".join(str(s) for s in skipped) if skipped else "nobody"
        beats.append(
            _beat(
                f"Route the packet to {payload.get('spender_approver_name')}. Skipped (OOO): {skip_txt}.",
                [payload.get("spender_approver_id")],
            )
        )
    return beats


def _clause(body: str) -> str:
    if not body:
        return ""
    cleaned = body.replace("#", "").strip()
    if "—" in cleaned:
        cleaned = cleaned.split("—", 1)[-1].strip()
    snippet = cleaned[:160]
    if len(cleaned) > 160:
        snippet = snippet.rsplit(" ", 1)[0] + "…"
    return snippet


def _beat(text: str, highlight: list[Any] | None = None) -> dict[str, Any]:
    return {
        "text": text.strip(),
        "highlight": [h for h in (highlight or []) if h],
    }
