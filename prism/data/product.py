"""Fictional product definition — Ledgerflow.

PRISM is demonstrated as if built for Ledgerflow, a fictional
AI-native accounting automation platform.
"""

PRODUCT_NAME = "Ledgerflow"
PRODUCT_TAGLINE = "The accounting platform that closes your books while you sleep."

PRODUCT_DESCRIPTION = (
    "Ledgerflow is an AI-native accounting automation platform built for "
    "high-growth SaaS and technology companies outgrowing QuickBooks. "
    "It automates month-end close, ASC 606 revenue recognition, "
    "multi-entity consolidation, real-time financial reporting, and "
    "AI-powered anomaly detection."
)

KEY_CAPABILITIES = [
    "Automated month-end close (15-20 days → 3-5 days)",
    "ASC 606 revenue recognition for complex SaaS billing",
    "Multi-entity consolidation without spreadsheets",
    "Real-time financial reporting dashboards",
    "AI-powered anomaly detection",
    "Audit-ready output with SOC 2-aligned documentation",
]

PROOF_POINTS = [
    "Average close time reduction: 72% (from 18 days to 5 days)",
    "Implementation time: 2-3 weeks vs. 3-6 months for NetSuite",
    "150+ SaaS companies from Series A to Series D",
    "Automated 2M+ journal entries in 2025",
    "$0 in implementation consulting fees (self-serve + AI-guided)",
    "SOC 2 Type II compliant",
    "99.97% uptime",
]

INTEGRATIONS = {
    "banking": ["Plaid-based bank feeds (all major US banks)"],
    "payments": ["Stripe", "Brex", "Ramp", "Mercury", "SVB"],
    "billing": ["Stripe Billing", "Chargebee", "Recurly", "Zuora"],
    "hris_payroll": ["Rippling", "Gusto", "Deel"],
    "erp_migration": ["QuickBooks Online", "QuickBooks Desktop", "Xero", "early-stage NetSuite"],
    "data_warehouse": ["Snowflake", "BigQuery", "Redshift"],
}

DIRECT_COMPETITORS = {
    "Rillet": "Closest competitor. Strong on core accounting, weaker on multi-entity. "
              "Ledgerflow differentiates on AI capabilities and ASC 606 depth.",
    "Puzzle": "Targets earlier stage (Seed/Series A). Less robust for scaling companies.",
    "Digits": "More focused on financial reporting/dashboards than core accounting automation.",
    "Numeric": "Close analytics and reporting layer. Not a full accounting platform.",
}

DISPLACEMENT_TARGETS = {
    "QuickBooks Online": "The default everyone starts with. Primary acquisition motion.",
    "NetSuite": "The 'enterprise' option. Expensive, slow, requires consultants. "
                "Ledgerflow positions as 'NetSuite-grade without the NetSuite pain.'",
    "Spreadsheets": "The real competitor. Many supplement QBO with extensive spreadsheet processes.",
}

BUYER_PERSONAS = {
    "champion": {
        "title": "VP Finance / Controller",
        "cares_about": "Month-end close time, team efficiency, accuracy, career impact",
        "language": "Operational, specific, metrics-focused",
    },
    "economic_buyer": {
        "title": "CFO / CEO",
        "cares_about": "Cost of current approach, audit readiness, board confidence, time-to-close reduction",
        "language": "Strategic, ROI-focused, risk-aware",
    },
    "technical_gatekeeper": {
        "title": "CTO / VP Engineering",
        "cares_about": "API quality, data model, integration architecture, security, build-vs-buy",
        "language": "Technical, skeptical, wants documentation",
    },
    "user": {
        "title": "Staff Accountant / Senior Accountant",
        "cares_about": "Daily workflow pain, manual reconciliation burden, month-end stress",
        "language": "Practical, frustrated, wants things to 'just work'",
    },
}
