"""Pydantic contracts for each ICM stage.

The LLM is forced to emit JSON that validates here *before* anything is
written to output.md. That split (structured object → markdown render) is
what keeps the filesystem human-readable without letting the model free-form
its way into unparseable state.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ContextBudget(BaseModel):
    """Token accounting shown in the cockpit — evidence that we did not
    load the whole workspace. Counts are estimated (chars/4), not billed.
    """

    layer_0_2: int = 0
    layer_3: int = 0
    layer_4: int = 0
    retrieval: int = 0
    total: int = 0
    monolithic_estimate: int = 42_000


class IntakeResult(BaseModel):
    request_id: str
    requester_id: str
    requester_name: str
    requester_role: str
    department: str
    manager_id: str | None
    manager_name: str | None
    manager_out_of_office: bool = False
    requester_threshold_usd: int
    item: str
    vendor_hint: str
    category: str
    amount_usd: float
    seats: int
    urgency: Literal["low", "normal", "high"] = "normal"
    business_justification: str
    exceeds_requester_threshold: bool
    notes: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        flags = "yes" if self.exceeds_requester_threshold else "no"
        ooo = "OOO" if self.manager_out_of_office else "in office"
        notes = "\n".join(f"- {n}" for n in self.notes) or "- none"
        return f"""# Intake packet — {self.request_id}

| Field | Value |
|---|---|
| Requester | {self.requester_name} ({self.requester_id}) |
| Role | {self.requester_role} |
| Department | {self.department} |
| Own threshold | ${self.requester_threshold_usd:,.0f} |
| Manager | {self.manager_name} ({self.manager_id}) — {ooo} |
| Item | {self.item} |
| Vendor hint | {self.vendor_hint} |
| Category | {self.category} |
| Amount | ${self.amount_usd:,.0f} |
| Seats | {self.seats} |
| Urgency | {self.urgency} |
| Exceeds own threshold | {flags} |

## Business justification

{self.business_justification}

## Notes

{notes}
"""


class PolicyFinding(BaseModel):
    policy_id: str
    title: str
    applies: bool
    requirement: str
    status: Literal["pass", "condition", "fail"]


class ComplianceResult(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    findings: list[PolicyFinding]
    required_reviews: list[str]
    blockers: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    summary: str

    def to_markdown(self) -> str:
        rows = "\n".join(
            f"| {f.policy_id} | {f.title} | {f.status} | {f.requirement} |"
            for f in self.findings
        )
        reviews = "\n".join(f"- {r}" for r in self.required_reviews) or "- none"
        blockers = "\n".join(f"- {b}" for b in self.blockers) or "- none"
        conditions = "\n".join(f"- {c}" for c in self.conditions) or "- none"
        return f"""# Compliance memo

**Risk level:** {self.risk_level}

{self.summary}

## Policy findings

| ID | Title | Status | Requirement |
|---|---|---|---|
{rows}

## Required reviews

{reviews}

## Blockers

{blockers}

## Conditions (may proceed once met)

{conditions}
"""


class VendorScore(BaseModel):
    vendor_id: str
    name: str
    compliance_score: int
    recommended_tier: str
    annual_usd: float
    soc2: bool
    preferred: bool
    incumbent: bool
    eligible: bool
    rationale: str


class SourcingResult(BaseModel):
    category: str
    primary_vendor_id: str
    primary_vendor_name: str
    primary_tier: str
    primary_annual_usd: float
    alternative_vendor_id: str
    alternative_vendor_name: str
    continuity_exemption: bool
    scores: list[VendorScore]
    summary: str

    def to_markdown(self) -> str:
        rows = "\n".join(
            f"| {s.name} | {s.recommended_tier} | ${s.annual_usd:,.0f} | {s.compliance_score} | "
            f"{'yes' if s.eligible else 'no'} | {s.rationale} |"
            for s in self.scores
        )
        exemption = "claimed (preferred incumbent)" if self.continuity_exemption else "not claimed"
        return f"""# Sourcing memo — {self.category}

**Primary:** {self.primary_vendor_name} · {self.primary_tier} · ${self.primary_annual_usd:,.0f}  
**Alternative:** {self.alternative_vendor_name}  
**Continuity exemption (POL-FIN-008 / POL-FIN-021):** {exemption}

{self.summary}

## Scorecard

| Vendor | Tier | Annual | Score | Eligible | Rationale |
|---|---|---|---|---|---|
{rows}
"""


class NegotiationResult(BaseModel):
    vendor_id: str
    vendor_name: str
    target_tier: str
    list_price_usd: float
    ask_price_usd: float
    term_months: int
    asks: list[str]
    batna: str
    walk_away: str
    must_have_clauses: list[str]
    summary: str

    def to_markdown(self) -> str:
        asks = "\n".join(f"- {a}" for a in self.asks)
        clauses = "\n".join(f"- {c}" for c in self.must_have_clauses)
        discount = 0.0
        if self.list_price_usd:
            discount = (self.list_price_usd - self.ask_price_usd) / self.list_price_usd * 100
        return f"""# Negotiation brief — {self.vendor_name}

| | |
|---|---|
| Target tier | {self.target_tier} |
| List | ${self.list_price_usd:,.0f} |
| Ask | ${self.ask_price_usd:,.0f} ({discount:.0f}% off) |
| Term | {self.term_months} months |

{self.summary}

## Asks

{asks}

## BATNA

{self.batna}

## Walk-away

{self.walk_away}

## Must-have order-form clauses

{clauses}
"""


class RoutingHop(BaseModel):
    employee_id: str
    name: str
    role: str
    threshold_usd: int
    out_of_office: bool
    action: Literal["requester", "skipped_ooo", "spender_approver", "informed", "functional_reviewer"]
    reason: str


class ApprovalResult(BaseModel):
    spender_approver_id: str
    spender_approver_name: str
    skipped: list[str]
    hops: list[RoutingHop]
    functional_reviewers: list[str]
    ready_to_route: bool
    summary: str

    def to_markdown(self) -> str:
        hops = "\n".join(
            f"| {h.name} | {h.role} | ${h.threshold_usd:,.0f} | {h.action} | {h.reason} |"
            for h in self.hops
        )
        skipped = ", ".join(self.skipped) or "none"
        reviewers = "\n".join(f"- {r}" for r in self.functional_reviewers)
        return f"""# Approval routing packet

**Spender approver:** {self.spender_approver_name} (`{self.spender_approver_id}`)  
**Skipped (OOO):** {skipped}  
**Ready to route:** {'yes' if self.ready_to_route else 'no'}

{self.summary}

## Chain

| Person | Role | Threshold | Action | Reason |
|---|---|---|---|---|
{hops}

## Functional reviewers (from compliance)

{reviewers}
"""


STAGE_SCHEMAS: dict[str, type[BaseModel]] = {
    "01_intake": IntakeResult,
    "02_compliance_check": ComplianceResult,
    "03_vendor_sourcing": SourcingResult,
    "04_negotiation_strategy": NegotiationResult,
    "05_approval_routing": ApprovalResult,
}
