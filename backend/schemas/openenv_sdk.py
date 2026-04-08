from __future__ import annotations

from typing import Any

from openenv.core import Action, Observation
from pydantic import Field

from backend.schemas.env import EmailMessage, HumanFeedbackEntry, TaskDefinition, ThreadMessage


class EmailTriageOpenEnvAction(Action):
    category: str | None = None
    priority: str | None = None
    department: str | None = None
    spam: int | None = None
    sentiment: str | None = None
    urgency: str | None = None
    response_draft: str | None = None
    escalation: bool = False
    confidence: float | None = None
    internal_note: str | None = None
    request_human_review: bool = False
    assigned_owner: str | None = None
    resolution_eta_hours: int | None = None
    customer_follow_up_required: bool = False
    escalation_target: str = "none"


class EmailTriageOpenEnvObservation(Observation):
    environment_id: str
    episode_id: str
    step_count: int
    max_steps: int
    current_turn: int = 1
    turn_label: str = "Initial Triage"
    task: TaskDefinition
    email: EmailMessage
    thread_messages: list[ThreadMessage] = Field(default_factory=list)
    pending_actions: list[str] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    latest_prediction: dict[str, Any] = Field(default_factory=dict)
    human_feedback: list[HumanFeedbackEntry] = Field(default_factory=list)
    last_grade: dict[str, Any] = Field(default_factory=dict)
    sla_status: str = "healthy"
    escalation_level: str = "none"
    human_review_required: bool = False
    reward_total: float = 0.0
    completion_score: float = 0.0
    queue_depth: int = 0
    pending_sla_breaches: int = 0
    reviewer_backlog: int = 0
    customer_history_summary: str = ""
    business_impact: str = ""
    suggested_departments: list[str] = Field(default_factory=list)
    ownership_status: str = "unassigned"
