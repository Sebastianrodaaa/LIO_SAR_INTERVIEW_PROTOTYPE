# {{stage}} — {{job}}

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
