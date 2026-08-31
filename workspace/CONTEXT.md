# Pipeline contract — software procurement

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
