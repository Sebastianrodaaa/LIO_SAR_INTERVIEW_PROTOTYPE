"""Hat metadata for the single agent. Not a swarm — one model, five contracts."""

from __future__ import annotations

HATS: dict[str, dict[str, str]] = {
    "01_intake": {
        "hat": "Intake analyst",
        "question": "Who wants this, and what does it cost?",
        "skip": "Vendor catalog, policy texts, and the approval walk stay on disk.",
        "handoff": "Next hat: Policy reviewer. It reads this output.md and matching policies only.",
        "caption": "Highlighting the person who asked, and the manager they report to.",
    },
    "02_compliance_check": {
        "hat": "Policy reviewer",
        "question": "Which company policies apply to this purchase?",
        "skip": "Org chart beyond the requester, and vendor price lists, are not this hat’s job.",
        "handoff": "Next hat: Sourcing analyst. It gets this memo plus in-category vendors only.",
        "caption": "Highlighting the policies that apply — spend, security, and legal.",
    },
    "03_vendor_sourcing": {
        "hat": "Sourcing analyst",
        "question": "Is this the right tool, or is there a better option in-category?",
        "skip": "Out-of-category vendors and the full employee directory are not loaded.",
        "handoff": "Next hat: Commercial negotiator. It only needs the chosen vendor’s tiers and SLA.",
        "caption": "Highlighting vendors in this category — not every product the company buys.",
    },
    "04_negotiation_strategy": {
        "hat": "Commercial negotiator",
        "question": "What price, term, and contract terms are reasonable?",
        "skip": "Re-loading the org chart or the full policy corpus. Already decided upstream.",
        "handoff": "Next hat: Routing clerk. It walks REPORTS_TO and skips anyone out of office.",
        "caption": "Focusing on the recommended vendor and its pricing.",
    },
    "05_approval_routing": {
        "hat": "Routing clerk",
        "question": "Who can actually sign, given limits and who is away?",
        "skip": "Vendor pricing. Already on disk from the last hat.",
        "handoff": "Pipeline complete. One model, five contracts, five focused prompts.",
        "caption": "Walking the reporting line, skipping anyone out of office, until someone’s limit covers the amount.",
    },
}
