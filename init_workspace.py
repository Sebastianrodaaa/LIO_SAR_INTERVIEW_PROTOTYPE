#!/usr/bin/env python3
"""Scaffold the ICM workspace — folder structure as the state machine.

Interpretable Context Methodology (Van Clief & McDermott, arXiv:2603.16021):
numbered folders encode order, CONTEXT.md files are stage contracts, and
output.md files are the human-editable handoff surfaces.

The orchestrator never stuffs the whole workspace into one prompt. Each
stage loads only its contract, its named references, the previous stage's
output, and a GraphRAG slice. That isolation is what prevents context
degradation (Liu et al., lost-in-the-middle).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "workspace"
PIPELINE = WORKSPACE / "pipeline"

# Pipeline form (ICM): one repeating unit of work = one procurement request.
# Human pauses become stage boundaries. Factory (_shared) is stable; product
# (each output.md) is unique per run.
STAGES = [
    "01_intake",
    "02_compliance_check",
    "03_vendor_sourcing",
    "04_negotiation_strategy",
    "05_approval_routing",
]


ROOT_CLAUDE = """# Northstar Procurement Workspace

Identity: single-agent ICM pipeline for software procurement. One model, five
numbered stages, filesystem as the state machine. Not a multi-agent swarm.

## Where things live

| Path | Role |
|---|---|
| `CONTEXT.md` | Pipeline contract (Layer 1) |
| `pipeline/01_intake` … `05_approval_routing` | Sequential stages |
| `pipeline/<stage>/CONTEXT.md` | Stage contract (Layer 2) |
| `pipeline/<stage>/output.md` | Working artifact (Layer 4) — human edit surface |
| `_shared/` | Factory reference: schemas, voice, routing notes (Layer 3) |
| `_templates/stage/` | Copy this to instantiate a new stage |
| `../data/` | Mock enterprise records (never load wholesale) |

## Where to go

- New request → `pipeline/01_intake/`
- Policy question → `02_compliance_check/` + GraphRAG policies
- Vendor compare → `03_vendor_sourcing/`
- Commercial terms → `04_negotiation_strategy/`
- Who signs → `05_approval_routing/` (OOO skip is graph-derived)

Status is whatever exists in each `output.md`. Do not hand-edit generated
indexes; regenerate with `python init_workspace.py` if a contract is missing.
"""


ROOT_CONTEXT = """# Pipeline contract — software procurement

Form: **Pipeline**. Repeating unit: one purchase request. Done: a signed
routing packet in `05_approval_routing/output.md`.

## Sequence

1. Intake — normalize the request.
2. Compliance — apply only the policies that govern this amount/category.
3. Vendor sourcing — score alternatives in-category.
4. Negotiation — commercial posture, not legal drafting.
5. Approval routing — walk REPORTS_TO, skip OOO, stop at covering threshold.

## Factory vs product

- Factory (stable): `_shared/*`, `../data/policies`, vendor directory.
- Product (this run): each stage `output.md`.

## Human gate

Nothing is "approved" by the model. A person reads `output.md`, edits if
needed, then continues. The next stage reads whatever is on disk.

## Token rule

Load the current CONTEXT.md + named inputs + GraphRAG bundle. Typical
budget 2k–8k tokens. Never concatenate all five stage prompts.
"""


SHARED_VOICE = """# Voice (factory)

Write like an internal procurement analyst at a serious company: precise,
calm, no marketing language. Use Northstar's real names and policy IDs.
Cite graph facts (employee id, policy id, vendor id) so a human can audit.
Never invent approvers or dollar amounts that are not in the retrieval bundle.
"""


SHARED_ROUTING = """# Graph retrieval notes (factory)

The orchestrator — not the model — decides the query. Stages must not
"browse" the whole employee directory.

| Stage | Retrieval |
|---|---|
| 01 | Requester node, department, manager, one-hop team |
| 02 | Policies whose GOVERNS/threshold match amount + category |
| 03 | Vendors with SUPPLIES = request category, plus scores |
| 04 | Chosen / incumbent vendor tiers, SLA, contract id |
| 05 | REPORTS_TO path; skip out_of_office; stop when threshold covers amount |
"""


STAGE_CONTRACTS: dict[str, str] = {
    "01_intake": """# 01 — Intake

One job: turn a raw purchase request into a structured intake record.

## Inputs

- Layer 3 (reference): `../../_shared/voice.md`
- Layer 3 (reference): GraphRAG bundle `requester` (employee, dept, manager)
- Layer 4 (working): JSON payload from `/run-procurement-cycle`

Do **not** load vendor catalogs, full policy texts, or later-stage contracts.

## Process

1. Identify requester against the graph (id, role, threshold, manager).
2. Normalize item, vendor hint, amount, seats, category, urgency.
3. Flag if amount exceeds the requester's own approval threshold (expected).
4. Write a factual summary. No policy rulings. No vendor bake-off.

## Outputs

- `output.md` — intake packet (rendered from the IntakeResult schema)

## Human check

Names, amount, and business justification are correct. If not, edit this
file; stage 02 reads whatever you leave.
""",
    "02_compliance_check": """# 02 — Compliance check

One job: apply only the policies that govern this request.

## Inputs

- Layer 3: `../../_shared/voice.md`
- Layer 3: GraphRAG bundle `policies` (full text of matching policies only)
- Layer 4: `../01_intake/output.md`

Do **not** load the vendor directory or the rest of the employee graph.

## Process

1. Read the intake amount, category, and seat count.
2. Evaluate each retrieved policy (spend threshold, SOC2, SSO/SCIM, OOO skip, DPA).
3. List required reviews (IT SecReview, Legal) as blockers or conditions.
4. Set a risk level. Do not pick a vendor.

## Outputs

- `output.md` — compliance memo (ComplianceResult schema)

## Human check

Policy IDs match Northstar documents. No extra reviews invented.
""",
    "03_vendor_sourcing": """# 03 — Vendor sourcing

One job: compare vendors that SUPPLY this category.

## Inputs

- Layer 3: `../../_shared/voice.md`
- Layer 3: GraphRAG bundle `vendors` (in-category only)
- Layer 4: `../01_intake/output.md`
- Layer 4: `../02_compliance_check/output.md`

Do **not** load out-of-category vendors (AWS, Datadog, …) or the org chart.

## Process

1. Keep only vendors in the request category that can meet SSO/SOC2 gates.
2. Score on compliance, price, incumbent/preferred status, switching cost.
3. Recommend a primary and a documented alternative (POL-FIN-008).
4. If incumbent + preferred, note the continuity exemption path.

## Outputs

- `output.md` — sourcing memo (SourcingResult schema)

## Human check

The recommended tier actually includes SSO/SCIM. Prices match the graph.
""",
    "04_negotiation_strategy": """# 04 — Negotiation strategy

One job: commercial posture for the recommended vendor. Not a legal draft.

## Inputs

- Layer 3: `../../_shared/voice.md`
- Layer 3: GraphRAG bundle `commercial` (tiers, SLA, contract id, score)
- Layer 4: `../03_vendor_sourcing/output.md`
- Layer 4: `../02_compliance_check/output.md` (conditions only)

Do **not** reload the full employee directory.

## Process

1. Name the target tier and list price.
2. Propose ask (discount, term, price-hold, SLA credit).
3. Walk-away and BATNA (the alternative from stage 03).
4. List legal/security conditions that must appear in the order form.

## Outputs

- `output.md` — negotiation brief (NegotiationResult schema)

## Human check

Asks are plausible against the list price. No invented contract IDs.
""",
    "05_approval_routing": """# 05 — Approval routing

One job: compute the live approval chain from the graph.

## Inputs

- Layer 3: `../../_shared/voice.md`
- Layer 3: GraphRAG bundle `approval_path` (REPORTS_TO walk, OOO flags, thresholds)
- Layer 4: `../01_intake/output.md` (amount, requester)
- Layer 4: `../02_compliance_check/output.md` (required reviewers)

Do **not** reload vendor pricing.

## Process

1. Start at the requester. Walk REPORTS_TO.
2. Skip any node with out_of_office = true (POL-PPL-009). Record the skip.
3. First in-office person whose threshold >= amount is the **spender approver**.
4. Attach required functional reviewers (IT Sec, Legal, Procurement) from stage 02.
5. Produce a routing ticket a human can execute.

## Seed expectation

Alex Rivera ($500) → Jordan Hale ($5k, OOO) skipped → Maya Chen ($50k) covers $15k.

## Outputs

- `output.md` — routing packet (ApprovalResult schema)

## Human check

Jordan Hale is skipped, not asked. Maya Chen is the spender approver.
""",
}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def init_workspace(reset_outputs: bool = True) -> Path:
    """Create or refresh the ICM tree. Contracts are factory; outputs are product."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    PIPELINE.mkdir(parents=True, exist_ok=True)

    _write(WORKSPACE / "CLAUDE.md", ROOT_CLAUDE)
    _write(WORKSPACE / "AGENTS.md", "See CLAUDE.md — this file is a pointer so agents and humans share one catalog.\n\n" + ROOT_CLAUDE)
    _write(WORKSPACE / "CONTEXT.md", ROOT_CONTEXT)
    _write(WORKSPACE / "_shared" / "voice.md", SHARED_VOICE)
    _write(WORKSPACE / "_shared" / "routing.md", SHARED_ROUTING)

    template = STAGE_CONTRACTS["01_intake"].replace("01 — Intake", "{{stage}} — {{job}}")
    _write(WORKSPACE / "_templates" / "stage" / "CONTEXT.md", template)
    _write(
        WORKSPACE / "_templates" / "stage" / "output.md",
        "<!-- copy this folder, then replace CONTEXT.md; leave output.md empty until the stage runs -->\n",
    )

    for stage in STAGES:
        folder = PIPELINE / stage
        folder.mkdir(parents=True, exist_ok=True)
        _write(folder / "CONTEXT.md", STAGE_CONTRACTS[stage])
        output = folder / "output.md"
        if reset_outputs or not output.exists():
            _write(
                output,
                f"# {stage} — awaiting run\n\nThis file is the Layer 4 edit surface. "
                "The orchestrator will overwrite it with validated structured output.\n",
            )

    print(f"ICM workspace ready at {WORKSPACE}")
    return WORKSPACE


if __name__ == "__main__":
    init_workspace()
