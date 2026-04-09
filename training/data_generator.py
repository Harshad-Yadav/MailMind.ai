from __future__ import annotations

import random
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

from training.constants import CATEGORY_TO_DEPARTMENT, CUSTOMER_TIERS, EMAIL_PATTERNS, SENTIMENT_SNIPPETS, SPAM_PATTERNS, URGENCY_SNIPPETS


@dataclass(slots=True)
class EmailRecord:
    email_id: str
    thread_id: str
    subject: str
    customer_name: str
    customer_tier: str
    received_at: str
    sla_due_at: str
    email_text: str
    category: str
    priority: str
    department: str
    sentiment: str
    spam: int
    urgency: str
    escalation_required: int
    draft_response: str


CUSTOMER_NAMES = [
    "Acme Health",
    "Northwind Logistics",
    "Greenline Capital",
    "Orbit Retail",
    "Pioneer Labs",
    "BluePeak Energy",
    "Evercore Media",
    "Redwood Telecom",
    "Lumina Travel",
    "Vertex Manufacturing",
]

SUBJECTS = {
    "billing": [
        "Invoice discrepancy requires review",
        "Unexpected renewal billing issue",
        "Duplicate charge on enterprise account",
    ],
    "technical_support": [
        "Platform outage affecting user access",
        "Critical bug blocking workflow",
        "Export failures after latest update",
    ],
    "sales": [
        "Request for enterprise pricing and demo",
        "Commercial discussion for expansion",
        "Evaluation timeline before procurement",
    ],
    "legal": [
        "Contract review and clause clarification",
        "DPA request for compliance review",
        "Urgent redline feedback needed",
    ],
    "human_resources": [
        "Confidential HR escalation",
        "Benefits enrollment correction",
        "Policy update request",
    ],
    "security": [
        "Potential security incident reported",
        "Urgent access anomaly investigation",
        "Customer audit evidence request",
    ],
    "operations": [
        "Operational SLA risk on batch jobs",
        "Integration issue delaying shipments",
        "Executive reporting support needed",
    ],
    "partnership": [
        "Partnership exploration and API access",
        "Reseller program discussion",
        "Co-marketing integration opportunity",
    ],
}


def _priority_from_signals(category: str, urgency: str, sentiment: str, customer_tier: str) -> str:
    score = 0
    score += {"low": 0, "medium": 1, "high": 2, "critical": 3}[urgency]
    score += {"positive": 0, "neutral": 0, "negative": 1, "frustrated": 2}[sentiment]
    score += {"free": 0, "pro": 0, "enterprise": 1, "strategic": 2}[customer_tier]
    if category in {"security", "legal"}:
        score += 1
    if score <= 1:
        return "low"
    if score <= 3:
        return "medium"
    if score <= 5:
        return "high"
    return "critical"


def _draft_response(category: str, department: str, priority: str, urgency: str, customer_name: str) -> str:
    return (
        f"Hello {customer_name},\n\n"
        f"Our {department} team has reviewed your {category.replace('_', ' ')} request. "
        f"We have marked it as {priority} priority with {urgency} urgency and assigned an owner. "
        f"We will share the next update before the current SLA window ends.\n\n"
        "Best,\nEnterprise Support"
    )


def _generate_ham_record(index: int, rng: random.Random) -> EmailRecord:
    category = rng.choice(list(EMAIL_PATTERNS))
    customer_name = rng.choice(CUSTOMER_NAMES)
    customer_tier = rng.choices(CUSTOMER_TIERS, weights=[0.15, 0.35, 0.35, 0.15], k=1)[0]
    urgency = rng.choices(["low", "medium", "high", "critical"], weights=[0.15, 0.45, 0.25, 0.15], k=1)[0]
    sentiment = rng.choices(["positive", "neutral", "negative", "frustrated"], weights=[0.15, 0.45, 0.25, 0.15], k=1)[0]
    priority = _priority_from_signals(category, urgency, sentiment, customer_tier)
    department = CATEGORY_TO_DEPARTMENT[category]
    now = datetime.now(UTC) - timedelta(minutes=rng.randint(0, 60 * 24 * 30))
    sla_hours = {"low": 72, "medium": 24, "high": 8, "critical": 1}[priority]
    subject = rng.choice(SUBJECTS[category])
    text = rng.choice(EMAIL_PATTERNS[category]).format(
        invoice_id=1000 + rng.randint(10, 999),
        error_code=500 + rng.randint(1, 20),
        seat_count=rng.choice([50, 100, 250, 500]),
        section_id=rng.choice(["4.2", "7.1", "9.4"]),
    )
    body = " ".join([
        text,
        rng.choice(SENTIMENT_SNIPPETS[sentiment]),
        rng.choice(URGENCY_SNIPPETS[urgency]),
        f"Our account tier is {customer_tier}.",
    ])
    return EmailRecord(
        email_id=f"email-{index:05d}",
        thread_id=f"thread-{rng.randint(1, 1500):04d}",
        subject=subject,
        customer_name=customer_name,
        customer_tier=customer_tier,
        received_at=now.isoformat(),
        sla_due_at=(now + timedelta(hours=sla_hours)).isoformat(),
        email_text=body,
        category=category,
        priority=priority,
        department=department,
        sentiment=sentiment,
        spam=0,
        urgency=urgency,
        escalation_required=int(priority == "critical" or category == "security"),
        draft_response=_draft_response(category, department, priority, urgency, customer_name),
    )


def _generate_spam_record(index: int, rng: random.Random) -> EmailRecord:
    now = datetime.now(UTC) - timedelta(minutes=rng.randint(0, 60 * 24 * 30))
    customer_name = rng.choice(CUSTOMER_NAMES)
    text = rng.choice(SPAM_PATTERNS)
    return EmailRecord(
        email_id=f"email-{index:05d}",
        thread_id=f"thread-{rng.randint(1501, 2000):04d}",
        subject="Guaranteed profit opportunity",
        customer_name=customer_name,
        customer_tier="free",
        received_at=now.isoformat(),
        sla_due_at=(now + timedelta(hours=72)).isoformat(),
        email_text=text,
        category="sales",
        priority="low",
        department="sales",
        sentiment="negative",
        spam=1,
        urgency="low",
        escalation_required=0,
        draft_response="No response required. Mark as spam and quarantine sender.",
    )


def build_dataset(rows: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    records: list[dict[str, object]] = []
    spam_count = max(250, rows // 12)
    ham_count = rows - spam_count

    for index in range(ham_count):
        records.append(asdict(_generate_ham_record(index=index, rng=rng)))
    for offset in range(spam_count):
        records.append(asdict(_generate_spam_record(index=ham_count + offset, rng=rng)))

    rng.shuffle(records)
    return pd.DataFrame.from_records(records)


def save_dataset(frame: pd.DataFrame, csv_path: str | Path, sqlite_path: str | Path | None = None) -> None:
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)
    if sqlite_path:
        sqlite_file = Path(sqlite_path)
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(sqlite_file) as connection:
            frame.to_sql("emails", connection, if_exists="replace", index=False)


def generate_and_save(rows: int = 5000, seed: int = 42) -> pd.DataFrame:
    frame = build_dataset(rows=rows, seed=seed)
    save_dataset(frame, "dataset/emails.csv", "dataset/email_triage.db")
    return frame


if __name__ == "__main__":
    try:
        generate_and_save()
        print("Data generation successful.")
    except Exception as e:
        print(f"Data generation failed: {e}. If this is building in a protected environment, ensure 'dataset/' is writable.")
