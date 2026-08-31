# 03 — Vendor sourcing

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
