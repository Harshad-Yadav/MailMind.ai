from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    email_id: str
    thread_id: str
    subject: str
    customer_name: str
    customer_tier: str
    received_at: str
    sla_due_at: str
    email_text: str


class ThreadMessage(BaseModel):
    message_id: str
    sender_role: Literal["customer", "agent", "reviewer", "system"]
    subject: str
    body: str
    created_at: str
    requires_response: bool = False
    tone: str | None = None


class HumanFeedbackEntry(BaseModel):
    feedback_id: str
    reviewer: str
    rating: int = Field(ge=1, le=5)
    verdict: Literal["approve", "revise", "escalate"]
    comments: str
    created_at: str


class AgentAction(BaseModel):
    category: str | None = None
    priority: str | None = None
    department: str | None = None
    spam: int | None = None
    sentiment: str | None = None
    urgency: str | None = None
    response_draft: str | None = None
    escalation: bool = False
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    internal_note: str | None = None
    request_human_review: bool = False
    assigned_owner: str | None = None
    resolution_eta_hours: int | None = Field(default=None, ge=0, le=168)
    customer_follow_up_required: bool = False
    escalation_target: Literal["none", "team_lead", "director", "executive"] = "none"


class TaskDefinition(BaseModel):
    task_id: str
    difficulty: Literal["easy", "medium", "hard"]
    title: str
    description: str
    required_outputs: list[str]
    reward_weights: dict[str, float]
    max_steps: int = 1
    supports_threading: bool = False


class TaskInstance(BaseModel):
    task: TaskDefinition
    email: EmailMessage
    expected: dict[str, Any]


class TriageObservation(BaseModel):
    environment_id: str
    episode_id: str
    task_id: str
    difficulty: Literal["easy", "medium", "hard"]
    step_count: int
    max_steps: int
    current_turn: int = 1
    turn_label: str = "Initial Triage"
    email: EmailMessage
    thread_messages: list[ThreadMessage] = Field(default_factory=list)
    pending_actions: list[str] = Field(default_factory=list)
    sla_status: Literal["healthy", "at_risk", "breached"] = "healthy"
    escalation_level: Literal["none", "team_lead", "director", "executive"] = "none"
    human_review_required: bool = False
    done: bool = False
    history_length: int = 0
    completion_score: float = Field(default=0.01, ge=0.0, le=1.0)
    queue_depth: int = 0
    pending_sla_breaches: int = 0
    reviewer_backlog: int = 0
    customer_history_summary: str = ""
    business_impact: str = ""
    suggested_departments: list[str] = Field(default_factory=list)
    ownership_status: Literal["unassigned", "assigned", "reassigned", "escalated"] = "unassigned"


class RewardSignal(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    matched: dict[str, bool] = Field(default_factory=dict)
    mistakes: list[str] = Field(default_factory=list)
    partial_progress: float = Field(default=0.01, ge=0.0, le=1.0)
    penalty_flags: list[str] = Field(default_factory=list)


class EnvironmentState(BaseModel):
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
    sla_status: Literal["healthy", "at_risk", "breached"] = "healthy"
    escalation_level: Literal["none", "team_lead", "director", "executive"] = "none"
    human_review_required: bool = False
    done: bool = False
    reward_total: float = 0.0
    completion_score: float = Field(default=0.01, ge=0.0, le=1.0)
    queue_depth: int = 0
    pending_sla_breaches: int = 0
    reviewer_backlog: int = 0
    customer_history_summary: str = ""
    business_impact: str = ""
    suggested_departments: list[str] = Field(default_factory=list)
    ownership_status: Literal["unassigned", "assigned", "reassigned", "escalated"] = "unassigned"


class ResetResponse(BaseModel):
    observation: TriageObservation
    state: EnvironmentState


class StepRequest(BaseModel):
    action: AgentAction


class StepResponse(BaseModel):
    observation: TriageObservation
    state: EnvironmentState
    reward: float = Field(ge=0.0, le=1.0)
    reward_detail: RewardSignal
    done: bool
    info: dict[str, Any]


class FeedbackRequest(BaseModel):
    reviewer: str
    rating: int = Field(ge=1, le=5)
    verdict: Literal["approve", "revise", "escalate"]
    comments: str


class FeedbackResponse(BaseModel):
    observation: TriageObservation
    state: EnvironmentState
    feedback: HumanFeedbackEntry
    reward_delta: float


class GraderResponse(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    reward: float = Field(ge=0.0, le=1.0)
    score_breakdown: dict[str, float]
    mistakes: list[str]
    matched: dict[str, bool]
    partial_progress: float = Field(ge=0.0, le=1.0)
    penalty_flags: list[str] = Field(default_factory=list)
