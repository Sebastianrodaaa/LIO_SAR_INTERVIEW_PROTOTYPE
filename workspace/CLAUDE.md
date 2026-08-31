# Northstar Procurement Workspace

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
