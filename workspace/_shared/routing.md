# Graph retrieval notes (factory)

The orchestrator — not the model — decides the query. Stages must not
"browse" the whole employee directory.

| Stage | Retrieval |
|---|---|
| 01 | Requester node, department, manager, one-hop team |
| 02 | Policies whose GOVERNS/threshold match amount + category |
| 03 | Vendors with SUPPLIES = request category, plus scores |
| 04 | Chosen / incumbent vendor tiers, SLA, contract id |
| 05 | REPORTS_TO path; skip out_of_office; stop when threshold covers amount |
