from __future__ import annotations

CATEGORIES = [
    "billing",
    "technical_support",
    "sales",
    "legal",
    "human_resources",
    "security",
    "operations",
    "partnership",
]

DEPARTMENTS = [
    "finance",
    "support",
    "sales",
    "legal",
    "people_ops",
    "security",
    "operations",
    "partnerships",
]

PRIORITIES = ["low", "medium", "high", "critical"]
SENTIMENTS = ["positive", "neutral", "negative", "frustrated"]
URGENCY_LEVELS = ["low", "medium", "high", "critical"]

CATEGORY_TO_DEPARTMENT = {
    "billing": "finance",
    "technical_support": "support",
    "sales": "sales",
    "legal": "legal",
    "human_resources": "people_ops",
    "security": "security",
    "operations": "operations",
    "partnership": "partnerships",
}

DEPARTMENT_TO_RESPONSE_TONE = {
    "finance": "helpful and precise",
    "support": "technical but empathetic",
    "sales": "warm and persuasive",
    "legal": "formal and careful",
    "people_ops": "respectful and supportive",
    "security": "urgent and procedural",
    "operations": "direct and action-oriented",
    "partnerships": "professional and collaborative",
}

EMAIL_PATTERNS = {
    "billing": [
        "We were charged twice for invoice INV-{invoice_id} and need a correction today.",
        "Our payment portal shows an overdue balance even though we paid last week.",
        "Please review unexpected fees added to our latest enterprise renewal quote.",
    ],
    "technical_support": [
        "Our SSO login is failing for all staff and the admin console returns error code {error_code}.",
        "Attachments are not syncing across devices after the recent release.",
        "The analytics dashboard is timing out whenever we export usage reports.",
    ],
    "sales": [
        "We are evaluating vendors and need pricing for {seat_count} enterprise seats.",
        "Can someone walk us through premium support and security add-ons for procurement?",
        "Our CTO wants a demo this week before budget approval closes.",
    ],
    "legal": [
        "Please send the latest DPA and confirm retention clauses for customer data in the EU.",
        "Our legal team flagged indemnification language in section {section_id} of the MSA.",
        "We need an urgent review of the contract redlines before signature.",
    ],
    "human_resources": [
        "A manager reported harassment concerns and needs confidential HR guidance immediately.",
        "Please update the employee parental leave policy linked in the handbook.",
        "We need help correcting benefits enrollment for a new hire.",
    ],
    "security": [
        "We detected suspicious login attempts from multiple regions and need incident support.",
        "A customer is requesting evidence for SOC2 controls and vulnerability management.",
        "Potential data exposure reported by a client; please investigate within the hour.",
    ],
    "operations": [
        "A warehouse integration is failing and shipments are stuck in pending status.",
        "Please expedite a workaround for nightly batch jobs missing SLA windows.",
        "Our executive briefing requires updated operational KPIs before 4 PM.",
    ],
    "partnership": [
        "We want to discuss a strategic integration partnership with a co-marketing launch.",
        "Our business development team is exploring reseller terms for Q4.",
        "Please share your partner API program requirements and revenue-share model.",
    ],
}

SENTIMENT_SNIPPETS = {
    "positive": [
        "Thanks in advance for the quick help.",
        "We appreciate the partnership and your responsiveness.",
        "Overall we have had a good experience so far.",
    ],
    "neutral": [
        "Please advise on next steps.",
        "Kindly confirm receipt and ownership.",
        "Looking forward to your update.",
    ],
    "negative": [
        "This issue is disrupting our team and needs attention.",
        "We are disappointed by the lack of clarity in the last reply.",
        "The current experience is below expectations.",
    ],
    "frustrated": [
        "This is unacceptable and we need leadership involved if not fixed now.",
        "We have followed up multiple times and still do not have resolution.",
        "Our executives are escalating this because the delay is costing us money.",
    ],
}

URGENCY_SNIPPETS = {
    "low": ["There is no immediate rush, but we would like an answer this week."],
    "medium": ["Please get back to us within one business day."],
    "high": ["This needs to be addressed before end of day to avoid customer impact."],
    "critical": ["Immediate action is required in the next hour to prevent severe impact."],
}

SPAM_PATTERNS = [
    "Congratulations! You have been selected for a guaranteed investment return with zero risk.",
    "URGENT ACCOUNT REWARD: verify your password now to unlock a bonus transfer.",
    "Exclusive crypto mining partnership, act immediately to double your income.",
]

CUSTOMER_TIERS = ["free", "pro", "enterprise", "strategic"]
