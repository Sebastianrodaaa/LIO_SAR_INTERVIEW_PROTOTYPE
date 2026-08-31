#!/usr/bin/env python3
"""Offline mock-data engine for the LIO SAR procurement prototype.

Generates a self-contained enterprise environment so the live demo never
touches a network. Output lives in ./data as JSON, Markdown policies, and
a SQLite snapshot.

This is Layer 3 *source material* (the factory). The ICM workspace does not
embed these records into prompts wholesale — GraphRAG retrieves only the
slice a given stage needs, which is how we avoid context degradation.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
POLICIES_DIR = DATA / "policies"


# ---------------------------------------------------------------------------
# Northstar Digital — fictional ~400-person SaaS company used for the demo.
# Seed scenario: Alex Rivera (Junior SWE, $500 threshold) requests a $15,000
# Figma Enterprise seat. Direct manager Jordan Hale is OOO, so approval
# walks REPORTS_TO to Maya Chen (VP Engineering, $50k threshold).
# ---------------------------------------------------------------------------

EMPLOYEES: list[dict] = [
    {
        "id": "emp-helena-voss",
        "name": "Helena Voss",
        "role": "Chief Executive Officer",
        "department": "Executive",
        "manager_id": None,
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 500_000,
        "email": "helena.voss@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-olivia-hart",
        "name": "Olivia Hart",
        "role": "Chief Financial Officer",
        "department": "Finance",
        "manager_id": "emp-helena-voss",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 100_000,
        "email": "olivia.hart@northstar.example",
        "location": "New York",
    },
    {
        "id": "emp-adrian-cole",
        "name": "Adrian Cole",
        "role": "General Counsel",
        "department": "Legal",
        "manager_id": "emp-helena-voss",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 75_000,
        "email": "adrian.cole@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-marcus-webb",
        "name": "Marcus Webb",
        "role": "Chief Information Security Officer",
        "department": "IT Security",
        "manager_id": "emp-helena-voss",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 50_000,
        "email": "marcus.webb@northstar.example",
        "location": "Austin",
    },
    {
        "id": "emp-maya-chen",
        "name": "Maya Chen",
        "role": "VP of Engineering",
        "department": "Engineering",
        "manager_id": "emp-helena-voss",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 50_000,
        "email": "maya.chen@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-dana-foster",
        "name": "Dana Foster",
        "role": "VP of Product",
        "department": "Product",
        "manager_id": "emp-helena-voss",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 50_000,
        "email": "dana.foster@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-grace-okada",
        "name": "Grace Okada",
        "role": "VP of People",
        "department": "People",
        "manager_id": "emp-helena-voss",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 40_000,
        "email": "grace.okada@northstar.example",
        "location": "Seattle",
    },
    {
        "id": "emp-harper-quinn",
        "name": "Harper Quinn",
        "role": "Head of Design",
        "department": "Design",
        "manager_id": "emp-dana-foster",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 25_000,
        "email": "harper.quinn@northstar.example",
        "location": "Los Angeles",
    },
    {
        "id": "emp-chris-lang",
        "name": "Chris Lang",
        "role": "Director of Platform",
        "department": "Engineering",
        "manager_id": "emp-maya-chen",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 15_000,
        "email": "chris.lang@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-jordan-hale",
        "name": "Jordan Hale",
        "role": "Engineering Manager",
        "department": "Engineering",
        "manager_id": "emp-maya-chen",
        "out_of_office": True,
        "ooo_until": "2026-09-07",
        "approval_threshold_usd": 5_000,
        "email": "jordan.hale@northstar.example",
        "location": "San Francisco",
        "ooo_note": "Parental leave. Do not route time-sensitive approvals.",
    },
    {
        "id": "emp-elena-vasquez",
        "name": "Elena Vasquez",
        "role": "Engineering Manager, Infrastructure",
        "department": "Engineering",
        "manager_id": "emp-chris-lang",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 5_000,
        "email": "elena.vasquez@northstar.example",
        "location": "Austin",
    },
    {
        "id": "emp-nina-patel",
        "name": "Nina Patel",
        "role": "IT Security Manager",
        "department": "IT Security",
        "manager_id": "emp-marcus-webb",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 10_000,
        "email": "nina.patel@northstar.example",
        "location": "Austin",
    },
    {
        "id": "emp-sophie-laurent",
        "name": "Sophie Laurent",
        "role": "Senior Counsel",
        "department": "Legal",
        "manager_id": "emp-adrian-cole",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 15_000,
        "email": "sophie.laurent@northstar.example",
        "location": "New York",
    },
    {
        "id": "emp-ben-shah",
        "name": "Ben Shah",
        "role": "Controller",
        "department": "Finance",
        "manager_id": "emp-olivia-hart",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 10_000,
        "email": "ben.shah@northstar.example",
        "location": "New York",
    },
    {
        "id": "emp-mei-lin",
        "name": "Mei Lin",
        "role": "Procurement Lead",
        "department": "Finance",
        "manager_id": "emp-ben-shah",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 7_500,
        "email": "mei.lin@northstar.example",
        "location": "New York",
    },
    {
        "id": "emp-priya-nair",
        "name": "Priya Nair",
        "role": "Staff Software Engineer",
        "department": "Engineering",
        "manager_id": "emp-jordan-hale",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 2_000,
        "email": "priya.nair@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-sam-okonkwo",
        "name": "Sam Okonkwo",
        "role": "Senior Software Engineer",
        "department": "Engineering",
        "manager_id": "emp-jordan-hale",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 1_000,
        "email": "sam.okonkwo@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-alex-rivera",
        "name": "Alex Rivera",
        "role": "Junior Software Engineer",
        "department": "Engineering",
        "manager_id": "emp-jordan-hale",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 500,
        "email": "alex.rivera@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-noah-kim",
        "name": "Noah Kim",
        "role": "Junior Software Engineer",
        "department": "Engineering",
        "manager_id": "emp-elena-vasquez",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 500,
        "email": "noah.kim@northstar.example",
        "location": "Austin",
    },
    {
        "id": "emp-riley-brooks",
        "name": "Riley Brooks",
        "role": "Product Manager",
        "department": "Product",
        "manager_id": "emp-dana-foster",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 2_000,
        "email": "riley.brooks@northstar.example",
        "location": "San Francisco",
    },
    {
        "id": "emp-jules-martin",
        "name": "Jules Martin",
        "role": "Product Designer",
        "department": "Design",
        "manager_id": "emp-harper-quinn",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 1_000,
        "email": "jules.martin@northstar.example",
        "location": "Los Angeles",
    },
    {
        "id": "emp-tom-becker",
        "name": "Tom Becker",
        "role": "IT Operations Specialist",
        "department": "IT Security",
        "manager_id": "emp-nina-patel",
        "out_of_office": False,
        "ooo_until": None,
        "approval_threshold_usd": 3_000,
        "email": "tom.becker@northstar.example",
        "location": "Austin",
    },
]

DEPARTMENTS: list[dict] = [
    {"id": "dept-executive", "name": "Executive", "cost_center": "CC-100"},
    {"id": "dept-engineering", "name": "Engineering", "cost_center": "CC-210"},
    {"id": "dept-product", "name": "Product", "cost_center": "CC-220"},
    {"id": "dept-design", "name": "Design", "cost_center": "CC-230"},
    {"id": "dept-finance", "name": "Finance", "cost_center": "CC-310"},
    {"id": "dept-legal", "name": "Legal", "cost_center": "CC-320"},
    {"id": "dept-itsec", "name": "IT Security", "cost_center": "CC-410"},
    {"id": "dept-people", "name": "People", "cost_center": "CC-510"},
]

VENDORS: list[dict] = [
    {
        "id": "vnd-figma",
        "name": "Figma",
        "category": "design-tools",
        "website": "https://www.figma.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 94,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "FIG-ENT-2025",
        "sla": "99.9% monthly uptime; P1 response 1h",
        "renewal": "2026-11-01",
        "pricing_tiers": [
            {"name": "Professional", "seats": 40, "annual_usd": 3_600},
            {"name": "Organization", "seats": 80, "annual_usd": 8_400},
            {"name": "Enterprise", "seats": 120, "annual_usd": 15_000},
        ],
        "notes": "Incumbent design system of record. Enterprise unlocks SSO + SCIM + branched libraries.",
    },
    {
        "id": "vnd-adobe",
        "name": "Adobe",
        "category": "design-tools",
        "website": "https://www.adobe.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 91,
        "preferred": False,
        "incumbent": False,
        "existing_contract": None,
        "sla": "99.9% uptime; P1 response 2h",
        "renewal": None,
        "pricing_tiers": [
            {"name": "Creative Cloud Teams", "seats": 40, "annual_usd": 23_980},
            {"name": "Creative Cloud Enterprise", "seats": 120, "annual_usd": 42_000},
        ],
        "notes": "Broader suite (Ps/Ai/Xd). Weak product-design collaboration vs Figma. Overlapping spend risk.",
    },
    {
        "id": "vnd-sketch",
        "name": "Sketch",
        "category": "design-tools",
        "website": "https://www.sketch.com",
        "soc2": True,
        "iso27001": False,
        "gdpr_dpa": True,
        "compliance_score": 78,
        "preferred": False,
        "incumbent": False,
        "existing_contract": None,
        "sla": "99.5% uptime; P1 response 4h",
        "renewal": None,
        "pricing_tiers": [
            {"name": "Mac + Cloud", "seats": 40, "annual_usd": 4_800},
            {"name": "Enterprise", "seats": 120, "annual_usd": 9_600},
        ],
        "notes": "macOS-only editor. Cheaper, but collaboration and FigJam-class workshops are weaker.",
    },
    {
        "id": "vnd-penpot",
        "name": "Penpot",
        "category": "design-tools",
        "website": "https://penpot.app",
        "soc2": False,
        "iso27001": False,
        "gdpr_dpa": True,
        "compliance_score": 61,
        "preferred": False,
        "incumbent": False,
        "existing_contract": None,
        "sla": "Best-effort community SLA; enterprise self-host optional",
        "renewal": None,
        "pricing_tiers": [
            {"name": "Cloud Team", "seats": 40, "annual_usd": 1_680},
            {"name": "Enterprise self-host", "seats": 120, "annual_usd": 7_200},
        ],
        "notes": "Open-source alternative. Fails SOC2 gate for production design-system hosting.",
    },
    {
        "id": "vnd-aws",
        "name": "Amazon Web Services",
        "category": "cloud-infrastructure",
        "website": "https://aws.amazon.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 97,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "AWS-EDP-2024",
        "sla": "Per-service SLA; enterprise TAM included",
        "renewal": "2027-01-15",
        "pricing_tiers": [
            {"name": "Pay-as-you-go", "seats": 0, "annual_usd": 420_000},
            {"name": "EDP commit", "seats": 0, "annual_usd": 380_000},
        ],
        "notes": "Primary cloud. Not in scope for this software-license request.",
    },
    {
        "id": "vnd-datadog",
        "name": "Datadog",
        "category": "observability",
        "website": "https://www.datadoghq.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 93,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "DD-PRO-2025",
        "sla": "99.99% uptime; P1 15m",
        "renewal": "2026-08-01",
        "pricing_tiers": [
            {"name": "Pro", "seats": 25, "annual_usd": 48_000},
            {"name": "Enterprise", "seats": 40, "annual_usd": 86_000},
        ],
        "notes": "Incumbent APM. Unrelated to design-tool sourcing.",
    },
    {
        "id": "vnd-slack",
        "name": "Slack",
        "category": "collaboration",
        "website": "https://slack.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 92,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "SLACK-ENT-2025",
        "sla": "99.99% uptime",
        "renewal": "2026-12-01",
        "pricing_tiers": [
            {"name": "Business+", "seats": 400, "annual_usd": 60_000},
            {"name": "Enterprise Grid", "seats": 400, "annual_usd": 96_000},
        ],
        "notes": "Company-wide comms. Not a Figma substitute.",
    },
    {
        "id": "vnd-notion",
        "name": "Notion",
        "category": "collaboration",
        "website": "https://www.notion.so",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 88,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "NOTION-ENT-2025",
        "sla": "99.9% uptime; P1 1h",
        "renewal": "2026-10-01",
        "pricing_tiers": [
            {"name": "Business", "seats": 400, "annual_usd": 38_400},
            {"name": "Enterprise", "seats": 400, "annual_usd": 72_000},
        ],
        "notes": "Wiki of record.",
    },
    {
        "id": "vnd-atlassian",
        "name": "Atlassian (Jira / Confluence)",
        "category": "collaboration",
        "website": "https://www.atlassian.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 90,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "ATL-CLOUD-2024",
        "sla": "99.9% Premium uptime",
        "renewal": "2026-09-15",
        "pricing_tiers": [
            {"name": "Premium", "seats": 250, "annual_usd": 42_000},
            {"name": "Enterprise", "seats": 250, "annual_usd": 78_000},
        ],
        "notes": "Issue tracker of record.",
    },
    {
        "id": "vnd-github",
        "name": "GitHub",
        "category": "developer-tools",
        "website": "https://github.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 96,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "GH-EMU-2025",
        "sla": "99.95% Actions + Git",
        "renewal": "2027-03-01",
        "pricing_tiers": [
            {"name": "Team", "seats": 180, "annual_usd": 8_640},
            {"name": "Enterprise", "seats": 180, "annual_usd": 37_800},
        ],
        "notes": "Source of truth for code.",
    },
    {
        "id": "vnd-okta",
        "name": "Okta",
        "category": "identity",
        "website": "https://www.okta.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 95,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "OKTA-SSO-2025",
        "sla": "99.99% uptime",
        "renewal": "2026-06-01",
        "pricing_tiers": [
            {"name": "SSO + MFA", "seats": 400, "annual_usd": 48_000},
            {"name": "Workforce Identity", "seats": 400, "annual_usd": 92_000},
        ],
        "notes": "IdP. Figma Enterprise is required for SCIM against Okta.",
    },
    {
        "id": "vnd-snowflake",
        "name": "Snowflake",
        "category": "data-platform",
        "website": "https://www.snowflake.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 94,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "SNOW-ENT-2025",
        "sla": "99.9% uptime",
        "renewal": "2026-12-15",
        "pricing_tiers": [
            {"name": "Standard", "seats": 20, "annual_usd": 85_000},
            {"name": "Enterprise", "seats": 40, "annual_usd": 140_000},
        ],
        "notes": "Warehouse. Out of scope.",
    },
    {
        "id": "vnd-linear",
        "name": "Linear",
        "category": "developer-tools",
        "website": "https://linear.app",
        "soc2": True,
        "iso27001": False,
        "gdpr_dpa": True,
        "compliance_score": 84,
        "preferred": False,
        "incumbent": False,
        "existing_contract": None,
        "sla": "99.9% uptime",
        "renewal": None,
        "pricing_tiers": [
            {"name": "Business", "seats": 80, "annual_usd": 9_600},
            {"name": "Enterprise", "seats": 80, "annual_usd": 16_800},
        ],
        "notes": "Evaluated as Jira alternative; not selected.",
    },
    {
        "id": "vnd-1password",
        "name": "1Password",
        "category": "identity",
        "website": "https://1password.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 93,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "1P-BIZ-2025",
        "sla": "99.99% uptime",
        "renewal": "2026-04-01",
        "pricing_tiers": [
            {"name": "Business", "seats": 400, "annual_usd": 38_400},
            {"name": "Enterprise", "seats": 400, "annual_usd": 52_800},
        ],
        "notes": "Secrets manager for teams.",
    },
    {
        "id": "vnd-crowdstrike",
        "name": "CrowdStrike",
        "category": "security",
        "website": "https://www.crowdstrike.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 96,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "CS-FALCON-2025",
        "sla": "99.9% cloud; 1h P1",
        "renewal": "2026-07-01",
        "pricing_tiers": [
            {"name": "Falcon Go", "seats": 400, "annual_usd": 36_000},
            {"name": "Falcon Complete", "seats": 400, "annual_usd": 120_000},
        ],
        "notes": "EDR of record.",
    },
    {
        "id": "vnd-twilio",
        "name": "Twilio",
        "category": "communications",
        "website": "https://www.twilio.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 89,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "TW-SMS-2025",
        "sla": "99.95% programmable messaging",
        "renewal": "2026-05-01",
        "pricing_tiers": [
            {"name": "Usage", "seats": 0, "annual_usd": 28_000},
            {"name": "Enterprise commit", "seats": 0, "annual_usd": 24_000},
        ],
        "notes": "SMS/voice. Out of scope.",
    },
    {
        "id": "vnd-sentry",
        "name": "Sentry",
        "category": "observability",
        "website": "https://sentry.io",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 90,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "SENTRY-BIZ-2025",
        "sla": "99.9% uptime",
        "renewal": "2026-09-01",
        "pricing_tiers": [
            {"name": "Team", "seats": 30, "annual_usd": 9_600},
            {"name": "Business", "seats": 30, "annual_usd": 24_000},
        ],
        "notes": "Error tracking.",
    },
    {
        "id": "vnd-hashicorp",
        "name": "HashiCorp",
        "category": "cloud-infrastructure",
        "website": "https://www.hashicorp.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 92,
        "preferred": True,
        "incumbent": True,
        "existing_contract": "HC-TERRAFORM-2025",
        "sla": "99.9% Terraform Cloud",
        "renewal": "2026-11-15",
        "pricing_tiers": [
            {"name": "Team", "seats": 20, "annual_usd": 14_400},
            {"name": "Standard", "seats": 40, "annual_usd": 48_000},
        ],
        "notes": "IaC. Out of scope.",
    },
    {
        "id": "vnd-mongodb",
        "name": "MongoDB",
        "category": "data-platform",
        "website": "https://www.mongodb.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 91,
        "preferred": False,
        "incumbent": False,
        "existing_contract": None,
        "sla": "99.95% Atlas",
        "renewal": None,
        "pricing_tiers": [
            {"name": "Dedicated M30", "seats": 0, "annual_usd": 18_000},
            {"name": "Dedicated M50", "seats": 0, "annual_usd": 42_000},
        ],
        "notes": "Evaluated vs Snowflake for operational JSON; not selected.",
    },
    {
        "id": "vnd-miro",
        "name": "Miro",
        "category": "design-tools",
        "website": "https://miro.com",
        "soc2": True,
        "iso27001": True,
        "gdpr_dpa": True,
        "compliance_score": 87,
        "preferred": False,
        "incumbent": False,
        "existing_contract": None,
        "sla": "99.9% uptime",
        "renewal": None,
        "pricing_tiers": [
            {"name": "Business", "seats": 80, "annual_usd": 12_960},
            {"name": "Enterprise", "seats": 120, "annual_usd": 19_200},
        ],
        "notes": "Workshop/whiteboard competitor to FigJam. Does not replace Figma Dev Mode.",
    },
]

POLICIES: list[dict] = [
    {
        "id": "pol-spend-10k",
        "title": "Software spend over $10,000",
        "governs": ["Engineering", "Product", "Design", "Finance"],
        "category_scope": ["design-tools", "developer-tools", "collaboration", "observability", "identity", "security", "data-platform", "cloud-infrastructure", "communications"],
        "threshold_usd": 10_000,
        "filename": "POL-FIN-014-spend-over-10k.md",
        "body": """# POL-FIN-014 — Software spend over $10,000

All software purchases with a first-year committed value **greater than $10,000 USD** require:

1. **IT SecReview** — completed by IT Security (owner: Nina Patel / Marcus Webb) before PO issuance.
2. **Legal sign-off** — DPA, liability cap, and data-processing addendum reviewed by Legal (owner: Sophie Laurent / Adrian Cole).
3. **Competitive sourcing** — at least two qualified alternatives documented, unless an incumbent-exemption is recorded.

Approval authority is the lowest person in the requester's reporting line whose `approval_threshold_usd` is greater than or equal to the committed amount. Out-of-office approvers are **skipped**; the request routes to the next in-office manager.

Finance must be copied on the final packet (Mei Lin, Procurement Lead).
""",
    },
    {
        "id": "pol-soc2",
        "title": "Vendor SOC 2 Type II requirement",
        "governs": ["IT Security", "Engineering", "Legal"],
        "category_scope": ["design-tools", "developer-tools", "collaboration", "observability", "identity", "security", "data-platform", "cloud-infrastructure"],
        "threshold_usd": 0,
        "filename": "POL-SEC-003-soc2-vendors.md",
        "body": """# POL-SEC-003 — Vendor SOC 2 Type II

Any vendor that will process, store, or view Northstar source code, designs, customer data, or employee PII **must** hold a current SOC 2 Type II report.

- ISO 27001 is accepted as a *supplement*, not a substitute.
- Exceptions require CISO written waiver (Marcus Webb) and expire in 90 days.
- Preferred-vendor list members are pre-cleared; non-preferred vendors start a full SecReview.
""",
    },
    {
        "id": "pol-ooo-routing",
        "title": "Out-of-office approval skip",
        "governs": ["Engineering", "Product", "Design", "Finance", "Legal", "IT Security", "People", "Executive"],
        "category_scope": ["all"],
        "threshold_usd": 0,
        "filename": "POL-PPL-009-ooo-approval-skip.md",
        "body": """# POL-PPL-009 — Out-of-office approval skip

If the would-be approver has `out_of_office = true`, the procurement system **must not wait**. Route to the next person on the `REPORTS_TO` path who is in office and whose threshold covers the amount.

Skip-level routing is auditable. The OOO manager is informed, not asked to approve.
""",
    },
    {
        "id": "pol-competitive-5k",
        "title": "Competitive quotes above $5,000",
        "governs": ["Finance", "Engineering", "Design"],
        "category_scope": ["design-tools", "developer-tools", "collaboration"],
        "threshold_usd": 5_000,
        "filename": "POL-FIN-008-competitive-quotes.md",
        "body": """# POL-FIN-008 — Competitive quotes above $5,000

Purchases over $5,000 require documentation of at least two alternatives (build vs buy, or two vendors). Incumbent tools may claim a **continuity exemption** if:

- The tool is on the preferred-vendor list, and
- Switching cost is quantified, and
- A 12-month price-hold or discount is requested in writing.

The exemption is recorded in the negotiation-strategy stage, not assumed.
""",
    },
    {
        "id": "pol-sso",
        "title": "SSO / SCIM for tools over 25 seats",
        "governs": ["IT Security", "Engineering"],
        "category_scope": ["design-tools", "collaboration", "developer-tools"],
        "threshold_usd": 0,
        "filename": "POL-SEC-011-sso-scim.md",
        "body": """# POL-SEC-011 — SSO and SCIM for tools over 25 seats

Any SaaS used by more than 25 employees must support:

- SAML or OIDC SSO against Okta
- SCIM 2.0 deprovisioning within 24 hours of Okta deactivation

Tiers that do not include SSO/SCIM are not eligible, even if cheaper.
""",
    },
    {
        "id": "pol-preferred-vendor",
        "title": "Preferred vendor continuity",
        "governs": ["Finance", "Engineering"],
        "category_scope": ["all"],
        "threshold_usd": 0,
        "filename": "POL-FIN-021-preferred-vendors.md",
        "body": """# POL-FIN-021 — Preferred vendor continuity

Preferred vendors (flagged in the vendor graph) receive first look. A net-new vendor in a category that already has a preferred incumbent requires a written switching-cost memo from the requester's VP.
""",
    },
    {
        "id": "pol-legal-dpa",
        "title": "Data processing addendum",
        "governs": ["Legal"],
        "category_scope": ["all"],
        "threshold_usd": 10_000,
        "filename": "POL-LGL-004-dpa.md",
        "body": """# POL-LGL-004 — Data processing addendum

Software over $10k that stores design files, source, or PII needs a signed DPA with:

- EU SCCs or UK IDTA as applicable
- Subprocessor list
- 72-hour breach notification
- Liability cap no lower than 12 months of fees

Legal owner: Sophie Laurent.
""",
    },
]


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_sqlite(path: Path) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE departments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cost_center TEXT
        );
        CREATE TABLE employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT,
            department TEXT,
            manager_id TEXT,
            out_of_office INTEGER,
            ooo_until TEXT,
            approval_threshold_usd INTEGER,
            email TEXT,
            location TEXT
        );
        CREATE TABLE vendors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            compliance_score INTEGER,
            preferred INTEGER,
            incumbent INTEGER,
            soc2 INTEGER,
            iso27001 INTEGER,
            sla TEXT,
            existing_contract TEXT
        );
        CREATE TABLE vendor_tiers (
            vendor_id TEXT,
            name TEXT,
            seats INTEGER,
            annual_usd INTEGER
        );
        CREATE TABLE policies (
            id TEXT PRIMARY KEY,
            title TEXT,
            threshold_usd INTEGER,
            filename TEXT
        );
        """
    )
    cur.executemany(
        "INSERT INTO departments VALUES (:id, :name, :cost_center)",
        DEPARTMENTS,
    )
    cur.executemany(
        """INSERT INTO employees
           (id, name, role, department, manager_id, out_of_office, ooo_until,
            approval_threshold_usd, email, location)
           VALUES
           (:id, :name, :role, :department, :manager_id, :out_of_office, :ooo_until,
            :approval_threshold_usd, :email, :location)""",
        [
            {
                **row,
                "out_of_office": int(row["out_of_office"]),
            }
            for row in EMPLOYEES
        ],
    )
    cur.executemany(
        """INSERT INTO vendors
           (id, name, category, compliance_score, preferred, incumbent, soc2, iso27001, sla, existing_contract)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                v["id"],
                v["name"],
                v["category"],
                v["compliance_score"],
                int(v["preferred"]),
                int(v["incumbent"]),
                int(v["soc2"]),
                int(v["iso27001"]),
                v["sla"],
                v["existing_contract"],
            )
            for v in VENDORS
        ],
    )
    tier_rows = []
    for vendor in VENDORS:
        for tier in vendor["pricing_tiers"]:
            tier_rows.append((vendor["id"], tier["name"], tier["seats"], tier["annual_usd"]))
    cur.executemany("INSERT INTO vendor_tiers VALUES (?, ?, ?, ?)", tier_rows)
    cur.executemany(
        "INSERT INTO policies VALUES (:id, :title, :threshold_usd, :filename)",
        POLICIES,
    )
    conn.commit()
    conn.close()


def generate() -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    POLICIES_DIR.mkdir(parents=True, exist_ok=True)

    _write_json(DATA / "employees.json", EMPLOYEES)
    _write_json(DATA / "departments.json", DEPARTMENTS)
    _write_json(DATA / "vendors.json", VENDORS)
    _write_json(DATA / "policies.json", POLICIES)

    _write_csv(
        DATA / "employees.csv",
        EMPLOYEES,
        [
            "id",
            "name",
            "role",
            "department",
            "manager_id",
            "out_of_office",
            "ooo_until",
            "approval_threshold_usd",
            "email",
            "location",
        ],
    )
    _write_csv(
        DATA / "vendors.csv",
        VENDORS,
        ["id", "name", "category", "compliance_score", "preferred", "incumbent", "soc2", "sla"],
    )

    for policy in POLICIES:
        (POLICIES_DIR / policy["filename"]).write_text(policy["body"].strip() + "\n", encoding="utf-8")

    _write_sqlite(DATA / "northstar.sqlite")

    seed = {
        "company": "Northstar Digital",
        "scenario": {
            "requester_id": "emp-alex-rivera",
            "vendor_id": "vnd-figma",
            "item": "Figma Enterprise",
            "amount_usd": 15_000,
            "seats": 120,
            "justification": (
                "Design and Engineering share one component library. Organization-tier "
                "lacks SCIM; POL-SEC-011 requires SSO/SCIM above 25 seats. Enterprise "
                "is the lowest compliant tier."
            ),
        },
    }
    _write_json(DATA / "seed_scenario.json", seed)
    print(f"Wrote mock enterprise data to {DATA}")
    return DATA


if __name__ == "__main__":
    generate()
