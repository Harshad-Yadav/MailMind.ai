from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from backend.core.config import get_settings
from backend.schemas.env import (
    AgentAction,
    EnvironmentState,
    FeedbackRequest,
    FeedbackResponse,
    GraderResponse,
    ResetResponse,
    RewardSignal,
    StepRequest,
    StepResponse,
    TaskDefinition,
    TriageObservation,
)
from backend.services.baseline_service import OpenAIBaselineService
from backend.services.dataset_service import DatasetService
from backend.services.env_service import OpenEnvEmailTriageEnvironment
from graders.email_grader import grade_action

router = APIRouter()
environment = OpenEnvEmailTriageEnvironment()
dataset_service = DatasetService()
settings = get_settings()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/metadata")
def metadata() -> dict[str, Any]:
    return {
        "name": settings.environment_name,
        "title": settings.project_name,
        "description": "Advanced enterprise email triage environment with multi-turn routing, priority, sentiment, SLA, spam, and escalation decisions.",
        "version": "1.0.0",
        "tags": ["openenv", "email-triage", "enterprise-workflow", "agent-training"],
    }


@router.get("/schema")
def schema() -> dict[str, Any]:
    return {
        "action": AgentAction.model_json_schema(),
        "observation": TriageObservation.model_json_schema(),
        "state": EnvironmentState.model_json_schema(),
        "reward": RewardSignal.model_json_schema(),
    }


@router.post("/mcp")
def mcp(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    request_payload = payload or {}
    return {
        "jsonrpc": "2.0",
        "id": request_payload.get("id"),
        "result": {
            "name": settings.environment_name,
            "status": "ok",
            "capabilities": ["reset", "step", "state", "tasks", "grader", "analytics"],
        },
    }


@router.post("/reset", response_model=ResetResponse)
def reset(task_id: str | None = None, seed: int | None = None) -> ResetResponse:
    state = environment.reset(task_id=task_id, seed=seed)
    return ResetResponse(observation=environment.observation(), state=state)


@router.get("/state", response_model=EnvironmentState)
def state() -> EnvironmentState:
    return environment.state()


@router.post("/step", response_model=StepResponse)
def step(request: StepRequest) -> StepResponse:
    return environment.step(request.action)


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    return environment.apply_feedback(request)


@router.get("/tasks", response_model=list[TaskDefinition])
def tasks() -> list[TaskDefinition]:
    return environment.available_tasks()


@router.post("/grader", response_model=GraderResponse)
def grader(request: StepRequest) -> GraderResponse:
    current = environment.current
    if current is None:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")
    return grade_action(task=current.task, action=request.action, expected=current.expected)


@router.get("/baseline")
def baseline(model: str | None = None, episodes_per_task: int = 3, seed: int = 42):
    service = OpenAIBaselineService()
    return service.run(model=model, episodes_per_task=episodes_per_task, seed=seed)


@router.get("/analytics")
def analytics():
    return {
        "dataset": dataset_service.analytics_snapshot(),
        "model_suggestion": environment.model_suggestion() if environment.current_state else None,
        "episode": environment.analytics_snapshot(),
    }
