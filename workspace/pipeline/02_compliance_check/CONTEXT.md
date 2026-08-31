# 02 — Compliance check

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
