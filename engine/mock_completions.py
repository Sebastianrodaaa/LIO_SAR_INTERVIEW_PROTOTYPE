"""Deterministic mock completions grounded in the GraphRAG bundle.

Used when LLM_PROVIDER=mock (the default for a 100% local demo). The
objects still pass through Pydantic validation — the only difference is
the JSON is authored here instead of by a hosted model. Swap the provider
to openai/anthropic and the same schemas, same files, same loop run.
"""

from __future__ import annotations

from typing import Any

from engine.schemas import (
    ApprovalResult,
    ComplianceResult,
    IntakeResult,
    NegotiationResult,
    PolicyFinding,
    RoutingHop,
    SourcingResult,
    VendorScore,
)


def complete_intake(request: dict[str, Any], retrieval: dict[str, Any]) -> IntakeResult:
    req = retrieval.get("requester") or {}
    mgr = retrieval.get("manager") or {}
    amount = float(request["amount_usd"])
    threshold = int(req.get("approval_threshold_usd") or 0)
    return IntakeResult(
        request_id=request.get("request_id", "PR-2026-0847"),
        requester_id=req.get("id") or request["requester_id"],
        requester_name=req.get("name") or "Unknown",
        requester_role=req.get("role") or "",
        department=req.get("department") or retrieval.get("department") or "",
        manager_id=mgr.get("id"),
        manager_name=mgr.get("name"),
        manager_out_of_office=bool(mgr.get("out_of_office")),
        requester_threshold_usd=threshold,
        item=request.get("item") or "Software license",
        vendor_hint=request.get("vendor_hint") or request.get("vendor_id") or "",
        category=request.get("category") or "design-tools",
        amount_usd=amount,
        seats=int(request.get("seats") or 0),
        urgency=request.get("urgency") or "normal",
        business_justification=request.get("justification") or "",
        exceeds_requester_threshold=amount > threshold,
        notes=[
            "Requester cannot self-approve — routing will be computed in stage 05.",
            "Manager OOO status is recorded here; skip logic is applied later so this stage stays single-purpose.",
        ],
    )


def complete_compliance(request: dict[str, Any], retrieval: dict[str, Any]) -> ComplianceResult:
    amount = float(retrieval.get("amount_usd") or request["amount_usd"])
    seats = int(retrieval.get("seats") or request.get("seats") or 0)
    findings: list[PolicyFinding] = []
    required: list[str] = []
    conditions: list[str] = []
    for policy in retrieval.get("policies") or []:
        pid = policy["id"]
        title = policy["title"]
        if pid == "pol-spend-10k":
            findings.append(
                PolicyFinding(
                    policy_id=pid,
                    title=title,
                    applies=amount > 10_000,
                    requirement="IT SecReview + Legal sign-off + competitive sourcing",
                    status="condition" if amount > 10_000 else "pass",
                )
            )
            if amount > 10_000:
                required.extend(
                    [
                        "IT SecReview — Nina Patel / Marcus Webb",
                        "Legal sign-off — Sophie Laurent / Adrian Cole",
                    ]
                )
                conditions.append("IT SecReview and Legal DPA before PO.")
        elif pid == "pol-soc2":
            findings.append(
                PolicyFinding(
                    policy_id=pid,
                    title=title,
                    applies=True,
                    requirement="Vendor must hold SOC 2 Type II",
                    status="condition",
                )
            )
            conditions.append("Selected vendor must be SOC 2 Type II (preferred list is pre-cleared).")
        elif pid == "pol-ooo-routing":
            findings.append(
                PolicyFinding(
                    policy_id=pid,
                    title=title,
                    applies=True,
                    requirement="Skip OOO approvers; do not wait",
                    status="pass",
                )
            )
        elif pid == "pol-competitive-5k":
            findings.append(
                PolicyFinding(
                    policy_id=pid,
                    title=title,
                    applies=amount > 5_000,
                    requirement="Two alternatives or incumbent continuity exemption",
                    status="condition",
                )
            )
            conditions.append("Stage 03 must document an alternative or claim the incumbent exemption.")
        elif pid == "pol-sso":
            findings.append(
                PolicyFinding(
                    policy_id=pid,
                    title=title,
                    applies=seats > 25,
                    requirement="SSO + SCIM against Okta",
                    status="condition" if seats > 25 else "pass",
                )
            )
            if seats > 25:
                conditions.append("Tier must include SAML/OIDC + SCIM 2.0.")
        elif pid == "pol-preferred-vendor":
            findings.append(
                PolicyFinding(
                    policy_id=pid,
                    title=title,
                    applies=True,
                    requirement="Preferred incumbent gets first look",
                    status="pass",
                )
            )
        elif pid == "pol-legal-dpa":
            findings.append(
                PolicyFinding(
                    policy_id=pid,
                    title=title,
                    applies=amount > 10_000,
                    requirement="Signed DPA, SCCs, 72h breach, cap ≥ 12 months fees",
                    status="condition" if amount > 10_000 else "pass",
                )
            )

    if not findings:
        findings.append(
            PolicyFinding(
                policy_id="pol-none",
                title="No matching policies",
                applies=False,
                requirement="n/a",
                status="pass",
            )
        )

    return ComplianceResult(
        risk_level="medium" if amount > 10_000 else "low",
        findings=findings,
        required_reviews=list(dict.fromkeys(required)),
        blockers=[],
        conditions=list(dict.fromkeys(conditions)),
        summary=(
            f"Committed value ${amount:,.0f}"
            + (
                " crosses the $10k software-spend policy. The packet is not blocked, "
                "but IT SecReview and Legal must sign before purchase order."
                if amount > 10_000
                else " stays under the $10k software-spend policy, so Legal/IT security sign-off is not forced by amount."
            )
            + (f" SSO/SCIM applies because seat count is {seats}." if seats > 25 else f" Seat count is {seats}, under the SSO/SCIM gate.")
        ),
    )


def complete_sourcing(request: dict[str, Any], retrieval: dict[str, Any]) -> SourcingResult:
    vendors = retrieval.get("vendors") or []
    scores: list[VendorScore] = []
    for vendor in vendors:
        tiers = vendor.get("pricing_tiers") or []
        # Prefer a tier that can cover ~120 seats if present; else last tier.
        chosen = None
        for tier in tiers:
            if tier.get("seats", 0) >= int(request.get("seats") or 0):
                chosen = tier
                break
        if not chosen and tiers:
            chosen = tiers[-1]
        eligible = bool(vendor.get("soc2")) and (
            (vendor.get("compliance_score") or 0) >= 75
        )
        if vendor.get("id") == "vnd-penpot":
            eligible = False
        scores.append(
            VendorScore(
                vendor_id=vendor.get("id") or "",
                name=vendor.get("name") or "",
                compliance_score=int(vendor.get("compliance_score") or 0),
                recommended_tier=(chosen or {}).get("name") or "n/a",
                annual_usd=float((chosen or {}).get("annual_usd") or 0),
                soc2=bool(vendor.get("soc2")),
                preferred=bool(vendor.get("preferred")),
                incumbent=bool(vendor.get("incumbent")),
                eligible=eligible,
                rationale=vendor.get("notes") or "",
            )
        )

    eligible_scores = [s for s in scores if s.eligible] or scores
    hinted = retrieval.get("hinted_vendor") or {}
    hinted_id = hinted.get("id")
    hinted_score = next((s for s in scores if hinted_id and s.vendor_id == hinted_id), None)
    if hinted_score:
        primary = hinted_score
    else:
        primary = next((s for s in eligible_scores if s.incumbent), eligible_scores[0])
    alternative = next(
        (s for s in eligible_scores if s.vendor_id != primary.vendor_id),
        eligible_scores[0],
    )

    if not primary.eligible:
        summary = (
            f"{primary.name} was requested but is not eligible "
            f"(SOC 2={primary.soc2}, score {primary.compliance_score}). "
            f"{alternative.name} remains the documented compliant path."
        )
    else:
        summary = (
            f"{primary.name} is the recommended path. {alternative.name} is the documented "
            "alternative."
        )

    return SourcingResult(
        category=retrieval.get("category") or request.get("category") or "",
        primary_vendor_id=primary.vendor_id,
        primary_vendor_name=primary.name,
        primary_tier=primary.recommended_tier,
        primary_annual_usd=primary.annual_usd,
        alternative_vendor_id=alternative.vendor_id,
        alternative_vendor_name=alternative.name,
        continuity_exemption=primary.incumbent and primary.preferred,
        scores=scores,
        summary=summary,
    )


def complete_negotiation(request: dict[str, Any], retrieval: dict[str, Any]) -> NegotiationResult:
    vendor = retrieval.get("vendor") or {}
    tiers = vendor.get("pricing_tiers") or []
    enterprise = next((t for t in tiers if "Enterprise" in t.get("name", "")), None) or (tiers[-1] if tiers else {})
    list_price = float(enterprise.get("annual_usd") or request.get("amount_usd") or 0)
    ask = round(list_price * 0.88)
    name = vendor.get("name") or "Vendor"
    return NegotiationResult(
        vendor_id=vendor.get("id") or "",
        vendor_name=name,
        target_tier=enterprise.get("name") or "Enterprise",
        list_price_usd=list_price,
        ask_price_usd=ask,
        term_months=24,
        asks=[
            f"12% first-year discount from ${list_price:,.0f} list to ${ask:,.0f}.",
            "24-month term with year-2 price hold.",
            "SSO/SCIM included (already in Enterprise) confirmed in writing.",
            "Quarterly SLA credits at 10% of monthly fee if uptime < 99.9%.",
        ],
        batna="Adobe Creative Cloud Enterprise is documented but switching cost (library migration, Dev Mode, FigJam) is high — use as leverage, not a real move.",
        walk_away="Do not accept a tier without SCIM. Do not accept liability cap below 12 months of fees.",
        must_have_clauses=[
            "DPA + SCCs (POL-LGL-004)",
            "Okta SAML + SCIM 2.0 (POL-SEC-011)",
            "SOC 2 Type II report current within 12 months",
            "Existing contract FIG-ENT-2025 novation / expansion rather than net-new MSA if possible",
        ],
        summary=(
            f"Incumbent expansion. Ask is commercial, not a rip-and-replace. {name} Enterprise "
            "list is already the compliant tier; the negotiation is price, term, and paper."
        ),
    )


def complete_approval(request: dict[str, Any], retrieval: dict[str, Any]) -> ApprovalResult:
    path = retrieval.get("path") or []
    covering = retrieval.get("covering_approver") or {}
    hops: list[RoutingHop] = []
    skipped: list[str] = []
    amount = float(retrieval.get("amount_usd") or request["amount_usd"])

    for index, node in enumerate(path):
        ooo = bool(node.get("out_of_office"))
        threshold = int(node.get("approval_threshold_usd") or 0)
        if index == 0:
            action = "requester"
            reason = "Opened the request; cannot self-approve."
        elif ooo:
            action = "skipped_ooo"
            reason = f"POL-PPL-009 skip — OOO until {node.get('ooo_until')}."
            skipped.append(node.get("name") or node.get("id"))
        elif node.get("id") == covering.get("id"):
            action = "spender_approver"
            reason = f"First in-office manager with threshold ${threshold:,.0f} ≥ ${amount:,.0f}."
        else:
            action = "informed"
            reason = "On the reporting path; not the covering approver."
        hops.append(
            RoutingHop(
                employee_id=node.get("id") or "",
                name=node.get("name") or "",
                role=node.get("role") or "",
                threshold_usd=threshold,
                out_of_office=ooo,
                action=action,
                reason=reason,
            )
        )

    functional = retrieval.get("functional_reviewers_hint") or []
    for name in functional:
        hops.append(
            RoutingHop(
                employee_id="functional",
                name=name.split(" — ")[0],
                role=name.split(" — ")[-1] if " — " in name else "Reviewer",
                threshold_usd=0,
                out_of_office=False,
                action="functional_reviewer",
                reason="Required by POL-FIN-014 / POL-LGL-004.",
            )
        )

    skipped_names = ", ".join(skipped) or "nobody"
    approver_name = covering.get("name") or "Unassigned"
    limit = covering.get("approval_threshold_usd")
    limit_txt = f"${limit:,.0f}" if limit else "unknown"
    return ApprovalResult(
        spender_approver_id=covering.get("id") or "",
        spender_approver_name=approver_name,
        skipped=skipped,
        hops=hops,
        functional_reviewers=functional,
        ready_to_route=bool(covering),
        summary=(
            f"${amount:,.0f}: skipped {skipped_names}. "
            f"Spender approver is {approver_name} ({limit_txt} limit). "
            "Nothing is purchased until a person signs."
        ),
    )


MOCK_BUILDERS = {
    "01_intake": complete_intake,
    "02_compliance_check": complete_compliance,
    "03_vendor_sourcing": complete_sourcing,
    "04_negotiation_strategy": complete_negotiation,
    "05_approval_routing": complete_approval,
}
