# POL-PPL-009 — Out-of-office approval skip

If the would-be approver has `out_of_office = true`, the procurement system **must not wait**. Route to the next person on the `REPORTS_TO` path who is in office and whose threshold covers the amount.

Skip-level routing is auditable. The OOO manager is informed, not asked to approve.
