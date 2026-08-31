# 05 — Approval routing

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
