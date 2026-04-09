from __future__ import annotations

from backend.schemas.env import TaskDefinition


TASKS: list[TaskDefinition] = [
    TaskDefinition(
        task_id="task-email-classification-easy",
        difficulty="easy",
        title="Email Classification",
        description="Predict the business category of an email.",
        required_outputs=["category"],
        reward_weights={"category": 1.0},
        max_steps=1,
        supports_threading=False,
    ),
    TaskDefinition(
        task_id="task-triage-medium",
        difficulty="medium",
        title="Classification and Priority",
        description="Classify the email and assign proper priority and routing.",
        required_outputs=["category", "priority", "department"],
        reward_weights={"category": 0.4, "priority": 0.3, "department": 0.3},
        max_steps=1,
        supports_threading=False,
    ),
    TaskDefinition(
        task_id="task-triage-plus",
        difficulty="medium",
        title="Triage with Sentiment",
        description="Full triage including sentiment and urgency analysis.",
        required_outputs=["category", "priority", "department", "sentiment", "urgency"],
        reward_weights={"category": 0.2, "priority": 0.2, "department": 0.2, "sentiment": 0.2, "urgency": 0.2},
        max_steps=1,
        supports_threading=False,
    ),
    TaskDefinition(
        task_id="task-full-enterprise-hard",
        difficulty="hard",
        title="Full Enterprise Triage",
        description="Handle multi-turn enterprise triage including routing, escalation, and human review gating.",
        required_outputs=["category", "priority", "department", "spam", "sentiment", "urgency", "response_draft", "escalation"],
        reward_weights={
            "category": 0.2,
            "priority": 0.15,
            "department": 0.15,
            "spam": 0.1,
            "sentiment": 0.1,
            "urgency": 0.1,
            "response_draft": 0.1,
            "escalation": 0.1,
        },
        max_steps=3,
        supports_threading=True,
    ),
]


TASK_MAP = {task.task_id: task for task in TASKS}
