from __future__ import annotations

from typing import Any

from openenv.core import Environment

from backend.schemas.env import AgentAction
from backend.schemas.openenv_sdk import EmailTriageOpenEnvAction, EmailTriageOpenEnvObservation
from backend.services.env_service import OpenEnvEmailTriageEnvironment


class EmailTriageSDKEnvironment(Environment):
    def __init__(self) -> None:
        super().__init__()
        self.runtime = OpenEnvEmailTriageEnvironment()

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **kwargs: Any,
    ) -> EmailTriageOpenEnvObservation:
        task_id = kwargs.get("task_id")
        state = self.runtime.reset(task_id=task_id, seed=seed)
        if episode_id:
            state.episode_id = episode_id
        return self._to_observation(state, reward=None)

    def step(
        self,
        action: EmailTriageOpenEnvAction,
        timeout_s: float | None = None,
        **kwargs: Any,
    ) -> EmailTriageOpenEnvObservation:
        payload = AgentAction(**action.model_dump(exclude={"metadata"}))
        result = self.runtime.step(payload)
        return self._to_observation(result.state, reward=result.reward)

    @property
    def state(self) -> EmailTriageOpenEnvObservation:
        current = self.runtime.state()
        return self._to_observation(current, reward=current.reward_total)

    def _to_observation(self, state, reward: float | None) -> EmailTriageOpenEnvObservation:
        return EmailTriageOpenEnvObservation(
            done=state.done,
            reward=reward,
            metadata={
                "environment_id": state.environment_id,
                "episode_id": state.episode_id,
                "task_id": state.task.task_id,
            },
            environment_id=state.environment_id,
            episode_id=state.episode_id,
            step_count=state.step_count,
            max_steps=state.max_steps,
            current_turn=state.current_turn,
            turn_label=state.turn_label,
            task=state.task,
            email=state.email,
            thread_messages=state.thread_messages,
            pending_actions=state.pending_actions,
            history=state.history,
            latest_prediction=state.latest_prediction,
            human_feedback=state.human_feedback,
            last_grade=state.last_grade,
            sla_status=state.sla_status,
            escalation_level=state.escalation_level,
            human_review_required=state.human_review_required,
            reward_total=state.reward_total,
            completion_score=state.completion_score,
            queue_depth=state.queue_depth,
            pending_sla_breaches=state.pending_sla_breaches,
            reviewer_backlog=state.reviewer_backlog,
            customer_history_summary=state.customer_history_summary,
            business_impact=state.business_impact,
            suggested_departments=state.suggested_departments,
            ownership_status=state.ownership_status,
        )
