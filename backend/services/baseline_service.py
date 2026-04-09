from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from backend.schemas.env import AgentAction, TriageObservation
from backend.services.env_service import OpenEnvEmailTriageEnvironment
from tasks.catalog import TASKS


class OpenAIBaselineService:
    def __init__(self) -> None:
        # Prioritize validator-injected variables
        api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("HF_TOKEN")
        raw_base_url = os.getenv("API_BASE_URL")
        
        if raw_base_url:
            base_url = raw_base_url.rstrip("/")
            if not base_url.endswith("/v1") and "googleapis.com" not in base_url:
                base_url = f"{base_url}/v1"
        else:
            base_url = None

        self.default_model = os.getenv("MODEL_NAME", "gpt-4-mini")
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

    def run(self, model: str | None = None, episodes_per_task: int = 3, seed: int = 42) -> dict[str, Any]:
        if self.client is None:
            raise RuntimeError("API_KEY or OPENAI_API_KEY must be configured before running the baseline.")

        chosen_model = model or self.default_model
        results: list[dict[str, Any]] = []
        overall_scores: list[float] = []
        overall_step_rewards: list[float] = []

        for task_index, task in enumerate(TASKS):
            task_episode_scores: list[float] = []
            task_step_rewards: list[float] = []
            episodes: list[dict[str, Any]] = []

            for episode_index in range(episodes_per_task):
                env = OpenEnvEmailTriageEnvironment()
                episode_seed = seed + (task_index * 100) + episode_index
                env.reset(task_id=task.task_id, seed=episode_seed)

                done = False
                trajectory: list[dict[str, Any]] = []
                while not done:
                    observation = env.observation()
                    action = self._solve_observation(chosen_model, task, observation)
                    result = env.step(action)
                    task_step_rewards.append(result.reward)
                    overall_step_rewards.append(result.reward)
                    trajectory.append(
                        {
                            "turn": observation.current_turn,
                            "reward": result.reward,
                            "done": result.done,
                            "matched": result.reward_detail.matched,
                            "mistakes": result.reward_detail.mistakes,
                            "penalty_flags": result.reward_detail.penalty_flags,
                        }
                    )
                    done = result.done

                final_state = env.state()
                episode_score = round(final_state.completion_score, 4)
                total_reward = round(final_state.reward_total, 4)
                task_episode_scores.append(episode_score)
                overall_scores.append(episode_score)
                episodes.append(
                    {
                        "seed": episode_seed,
                        "episode_score": episode_score,
                        "total_reward": total_reward,
                        "steps": final_state.step_count,
                        "history": trajectory,
                    }
                )

            results.append(
                {
                    "task_id": task.task_id,
                    "difficulty": task.difficulty,
                    "episodes": episodes,
                    "mean_episode_score": round(sum(task_episode_scores) / max(len(task_episode_scores), 1), 4),
                    "mean_step_reward": round(sum(task_step_rewards) / max(len(task_step_rewards), 1), 4),
                    "success_rate": round(
                        sum(1 for score in task_episode_scores if score >= 0.85) / max(len(task_episode_scores), 1),
                        4,
                    ),
                }
            )

        payload = {
            "model": chosen_model,
            "base_url": os.getenv("API_BASE_URL", "https://api.openai.com/v1"),
            "seed": seed,
            "episodes_per_task": episodes_per_task,
            "overall_mean_episode_score": round(sum(overall_scores) / max(len(overall_scores), 1), 4),
            "overall_mean_step_reward": round(sum(overall_step_rewards) / max(len(overall_step_rewards), 1), 4),
            "tasks": results,
        }
        output_path = Path("models/baselines")
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "openai_baseline_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def _solve_observation(self, model: str, task, observation: TriageObservation) -> AgentAction:
        prompt = self._build_prompt(task, observation)
        content = self._complete_json(model=model, prompt=prompt)
        parsed = self._parse_json(content)
        normalized = self._normalize_action_payload(parsed)
        return AgentAction(**normalized)

    def _complete_json(self, model: str, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=model,
                temperature=0,
                seed=42,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are an enterprise email triage agent. Return only strict JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content or "{}"
        except Exception:
            response = self.client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an enterprise email triage agent. Return only strict JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content or "{}"

    def _build_prompt(self, task, observation: TriageObservation) -> str:
        thread_excerpt = "\n\n".join(
            f"[{message.sender_role}] {message.subject}\n{message.body}"
            for message in observation.thread_messages[-4:]
        )
        return (
            f"Task ID: {task.task_id}\n"
            f"Task Difficulty: {task.difficulty}\n"
            f"Task Goal: {task.description}\n"
            f"Required Outputs: {', '.join(task.required_outputs)}\n"
            f"Current Turn: {observation.current_turn}/{observation.max_steps}\n"
            f"Turn Label: {observation.turn_label}\n"
            f"Pending Actions: {', '.join(observation.pending_actions)}\n"
            f"SLA Status: {observation.sla_status}\n"
            f"Escalation Level: {observation.escalation_level}\n"
            f"Human Review Required: {observation.human_review_required}\n"
            f"Queue Depth: {observation.queue_depth}\n"
            f"Pending SLA Breaches: {observation.pending_sla_breaches}\n"
            f"Reviewer Backlog: {observation.reviewer_backlog}\n"
            f"Ownership Status: {observation.ownership_status}\n"
            f"Business Impact: {observation.business_impact}\n"
            f"Customer History: {observation.customer_history_summary}\n"
            f"Suggested Departments: {', '.join(observation.suggested_departments)}\n\n"
            f"Subject: {observation.email.subject}\n"
            f"Customer: {observation.email.customer_name}\n"
            f"Customer Tier: {observation.email.customer_tier}\n"
            f"Received At: {observation.email.received_at}\n"
            f"SLA Due At: {observation.email.sla_due_at}\n"
            f"Email Body:\n{observation.email.email_text}\n\n"
            f"Thread Context:\n{thread_excerpt}\n\n"
            "Return a JSON object with exactly these keys: "
            "category, priority, department, spam, sentiment, urgency, response_draft, escalation, confidence, internal_note, request_human_review, assigned_owner, resolution_eta_hours, customer_follow_up_required, escalation_target. "
            "Use lowercase enum-like strings where appropriate, spam must be 0 or 1, escalation and request_human_review must be booleans, customer_follow_up_required must be boolean, resolution_eta_hours must be an integer, and confidence must be between 0 and 1."
        )

    def _parse_json(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}

    def _coerce_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    def _normalize_action_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            "category": str(payload.get("category", "operations")).strip().lower(),
            "priority": str(payload.get("priority", "medium")).strip().lower(),
            "department": str(payload.get("department", "operations")).strip().lower(),
            "spam": 1 if str(payload.get("spam", 0)).strip().lower() in {"1", "true", "spam", "yes"} else 0,
            "sentiment": str(payload.get("sentiment", "neutral")).strip().lower(),
            "urgency": str(payload.get("urgency", "medium")).strip().lower(),
            "response_draft": str(payload.get("response_draft", "We are reviewing your request and routing it to the appropriate team.")).strip(),
            "escalation": self._coerce_bool(payload.get("escalation", False)),
            "internal_note": str(payload.get("internal_note", "Triage completed.")).strip(),
            "request_human_review": self._coerce_bool(payload.get("request_human_review", False)),
            "assigned_owner": str(payload.get("assigned_owner", "ops-command-owner")).strip().lower(),
            "customer_follow_up_required": self._coerce_bool(payload.get("customer_follow_up_required", True)),
            "escalation_target": str(payload.get("escalation_target", "none")).strip().lower(),
        }

        confidence_raw = payload.get("confidence", 0.65)
        try:
            normalized["confidence"] = max(0.0, min(1.0, float(confidence_raw)))
        except (TypeError, ValueError):
            normalized["confidence"] = 0.65

        eta_raw = payload.get("resolution_eta_hours", 24)
        try:
            normalized["resolution_eta_hours"] = max(0, min(168, int(eta_raw)))
        except (TypeError, ValueError):
            normalized["resolution_eta_hours"] = 24

        return normalized
