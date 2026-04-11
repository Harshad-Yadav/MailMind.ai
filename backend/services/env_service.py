from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from backend.core.config import get_settings
from backend.db.sqlite import persist_episode, persist_step
from backend.schemas.env import (
    AgentAction,
    EmailMessage,
    EnvironmentState,
    FeedbackRequest,
    FeedbackResponse,
    HumanFeedbackEntry,
    RewardSignal,
    StepResponse,
    TaskInstance,
    ThreadMessage,
    TriageObservation,
)
from backend.services.dataset_service import DatasetService
from backend.services.inference_engine import InferenceEngine
from graders.email_grader import grade_action
from tasks.catalog import TASK_MAP, TASKS

_PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class OpenEnvEmailTriageEnvironment:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.dataset_service = DatasetService()
        self.inference_engine = InferenceEngine()
        self.current: TaskInstance | None = None
        self.current_state: EnvironmentState | None = None
        self.episode_plan: list[dict[str, object]] = []
        self.plan_index = 0

    def available_tasks(self):
        return TASKS

    def reset(self, task_id: str | None = None, seed: int | None = None) -> EnvironmentState:
        try:
            import random
            task = TASK_MAP[task_id] if task_id else TASKS[0]
            seed = seed if seed is not None else random.randint(0, 1000000)
            try:
                row = self.dataset_service.sample(seed=seed, spam_only=False)
            except Exception:
                row = self._fallback_row()
            
            queue_context = self._queue_context(row=row, task=task, seed=seed)
            self.episode_plan = self._build_episode_plan(row=row, task=task, queue_context=queue_context)
            self.plan_index = 0
            turn = self.episode_plan[0]
            self.current = TaskInstance(task=task, email=turn["email"], expected=turn["expected"])
            state = EnvironmentState(
                environment_id=self.settings.environment_name,
                episode_id=str(uuid4()),
                step_count=0,
                max_steps=len(self.episode_plan),
                current_turn=1,
                turn_label=str(turn["label"]),
                task=task,
                email=turn["email"],
                thread_messages=[turn["thread_message"]],
                pending_actions=list(turn["pending_actions"]),
                history=[],
                latest_prediction={},
                human_feedback=[],
                last_grade={},
                sla_status=str(turn["expected"].get("sla_status", "healthy")),
                escalation_level=self._escalation_level(turn["expected"]),
                human_review_required=bool(turn["expected"].get("human_review_required", False)),
                done=False,
                reward_total=0.0,
                completion_score=0.01,
                queue_depth=int(turn["context"]["queue_depth"]),
                pending_sla_breaches=int(turn["context"]["pending_sla_breaches"]),
                reviewer_backlog=int(turn["context"]["reviewer_backlog"]),
                customer_history_summary=str(turn["context"]["customer_history_summary"]),
                business_impact=str(turn["context"]["business_impact"]),
                suggested_departments=list(turn["context"]["suggested_departments"]),
                ownership_status=str(turn["context"]["ownership_status"]),
            )
            self.current_state = state
            try:
                persist_episode(state.episode_id, task.task_id, state.email.email_id, state.model_dump())
            except Exception:
                pass
            return state
        except Exception:
            fallback_state = EnvironmentState(
                environment_id=self.settings.environment_name,
                episode_id=str(uuid4()),
                step_count=0,
                max_steps=1,
                task=TASKS[0],
                email=EmailMessage(
                    email_id="fallback-id",
                    thread_id="fallback-thread",
                    subject="Environment Reset Failed",
                    customer_name="System",
                    customer_tier="none",
                    received_at=datetime.now(UTC).isoformat(),
                    sla_due_at=datetime.now(UTC).isoformat(),
                    email_text="Environment encountered a critical error during reset and is running in safety mode."
                ),
                done=True,
                reward_total=0.01,
                completion_score=0.01,
            )
            self.current_state = fallback_state
            return fallback_state

    def state(self) -> EnvironmentState:
        if self.current_state is None:
            return self.reset()
        return self.current_state

    def observation(self) -> TriageObservation:
        return self._observation_from_state(self.state())

    def model_suggestion(self) -> dict[str, object]:
        try:
            current = self.state()
            return self.inference_engine.predict(current.email.email_text, customer_name=current.email.customer_name)
        except Exception:
            return {}

    def analytics_snapshot(self) -> dict[str, object]:
        current = self.current_state
        if current is None:
            return {
                "current_episode": None,
                "suggested_action": None,
            }
        reward_curve = [float(item.get("reward", 0.0)) for item in current.history]
        matched_ratios = [
            sum(1 for value in (item.get("matched") or {}).values() if value) / max(len(item.get("matched") or {}), 1)
            for item in current.history
        ]
        avg_feedback = (
            round(sum(item.rating for item in current.human_feedback) / len(current.human_feedback), 2)
            if current.human_feedback
            else 0.0
        )
        return {
            "current_episode": {
                "episode_id": current.episode_id,
                "current_turn": current.current_turn,
                "max_steps": current.max_steps,
                "thread_length": len(current.thread_messages),
                "reward_curve": reward_curve,
                "matched_ratio_curve": matched_ratios,
                "feedback_count": len(current.human_feedback),
                "average_feedback_rating": avg_feedback,
                "pending_actions": current.pending_actions,
                "sla_status": current.sla_status,
                "escalation_level": current.escalation_level,
                "completion_score": current.completion_score,
                "queue_depth": current.queue_depth,
                "pending_sla_breaches": current.pending_sla_breaches,
                "reviewer_backlog": current.reviewer_backlog,
                "ownership_status": current.ownership_status,
            },
            "suggested_action": self.model_suggestion(),
        }

    def apply_feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        if self.current_state is None:
            self.reset()
        if self.current_state is None:
            # Should not happen given reset() protections
            raise RuntimeError("Environment failed to initialize")

        entry = HumanFeedbackEntry(
            feedback_id=str(uuid4()),
            reviewer=request.reviewer,
            rating=request.rating,
            verdict=request.verdict,
            comments=request.comments,
            created_at=datetime.now(UTC).isoformat(),
        )
        reward_delta = {"approve": 0.08, "revise": -0.04, "escalate": -0.08}[request.verdict] + ((request.rating - 3) * 0.02)
        self.current_state.human_feedback.append(entry)
        self.current_state.reward_total = round(self.current_state.reward_total + reward_delta, 4)
        self.current_state.completion_score = self._completion_score(self.current_state)
        if request.verdict == "escalate":
            self.current_state.ownership_status = "escalated"
        self.current_state.thread_messages.append(
            ThreadMessage(
                message_id=f"review-{len(self.current_state.human_feedback):02d}",
                sender_role="reviewer",
                subject="Reviewer Feedback",
                body=f"{request.verdict.upper()}: {request.comments}",
                created_at=entry.created_at,
                requires_response=request.verdict != "approve",
                tone="directive",
            )
        )
        if request.verdict != "approve":
            self.current_state.pending_actions = ["apply_reviewer_feedback", *self.current_state.pending_actions]
            self.current_state.human_review_required = True
        self.current_state.last_grade = {
            **self.current_state.last_grade,
            "feedback": entry.model_dump(),
            "reward_delta": round(reward_delta, 4),
        }
        try:
            persist_step(self.current_state.episode_id, reward_delta, self.current_state.done, self.current_state.model_dump())
        except Exception:
            pass
        return FeedbackResponse(
            observation=self._observation_from_state(self.current_state),
            state=deepcopy(self.current_state),
            feedback=entry,
            reward_delta=round(reward_delta, 4),
        )

    def step(self, action: AgentAction) -> StepResponse:
        try:
            if self.current is None or self.current_state is None:
                self.reset()
            
            if self.current is None or self.current_state is None:
                raise RuntimeError("Failed to reset environment")

            turn = self.episode_plan[self.plan_index]
            grade = grade_action(task=self.current.task, action=action, expected=self.current.expected)
            
            try:
                suggestion = self.inference_engine.predict(self.current.email.email_text, customer_name=self.current.email.customer_name)
            except Exception:
                suggestion = {}

            self.current_state.step_count += 1
            self.current_state.reward_total = round(self.current_state.reward_total + grade.reward, 4)
            self.current_state.ownership_status = self._ownership_status_from_action(action)
            agent_message = self._agent_thread_message(action=action, turn_label=str(turn["label"]), episode_step=self.current_state.step_count)
            self.current_state.thread_messages.append(agent_message)
            self.current_state.latest_prediction = {
                "agent_action": action.model_dump(),
                "model_suggestion": suggestion,
                "graded_at": datetime.now(UTC).isoformat(),
            }
            self.current_state.last_grade = {
                "score": grade.score,
                "reward": grade.reward,
                "score_breakdown": grade.score_breakdown,
                "mistakes": grade.mistakes,
                "matched": grade.matched,
                "partial_progress": grade.partial_progress,
                "penalty_flags": grade.penalty_flags,
            }
            self.current_state.history.append(
                {
                    "step": self.current_state.step_count,
                    "turn_label": self.current_state.turn_label,
                    "action": action.model_dump(),
                    "reward": grade.reward,
                    "score": grade.score,
                    "mistakes": grade.mistakes,
                    "matched": grade.matched,
                    "score_breakdown": grade.score_breakdown,
                    "partial_progress": grade.partial_progress,
                    "penalty_flags": grade.penalty_flags,
                }
            )

            info: dict[str, object] = {
                "score_breakdown": grade.score_breakdown,
                "mistakes": grade.mistakes,
                "matched": grade.matched,
                "partial_progress": grade.partial_progress,
                "penalty_flags": grade.penalty_flags,
                "suggestion": suggestion,
                "next_turn_generated": False,
            }

            has_next_turn = self.plan_index + 1 < len(self.episode_plan)
            if has_next_turn:
                self.plan_index += 1
                next_turn = self.episode_plan[self.plan_index]
                self.current = TaskInstance(task=self.current.task, email=next_turn["email"], expected=next_turn["expected"])
                self.current_state.email = next_turn["email"]
                self.current_state.current_turn = self.plan_index + 1
                self.current_state.turn_label = str(next_turn["label"])
                self.current_state.pending_actions = list(next_turn["pending_actions"])
                self.current_state.sla_status = str(next_turn["expected"].get("sla_status", "healthy"))
                self.current_state.escalation_level = self._escalation_level(next_turn["expected"])
                self.current_state.human_review_required = bool(next_turn["expected"].get("human_review_required", False))
                self.current_state.done = False
                self.current_state.queue_depth = int(next_turn["context"]["queue_depth"])
                self.current_state.pending_sla_breaches = int(next_turn["context"]["pending_sla_breaches"])
                self.current_state.reviewer_backlog = int(next_turn["context"]["reviewer_backlog"])
                self.current_state.customer_history_summary = str(next_turn["context"]["customer_history_summary"])
                self.current_state.business_impact = str(next_turn["context"]["business_impact"])
                self.current_state.suggested_departments = list(next_turn["context"]["suggested_departments"])
                self.current_state.thread_messages.append(next_turn["thread_message"])
                info["next_turn_generated"] = True
                info["next_turn_label"] = next_turn["label"]
            else:
                self.current_state.pending_actions = ["episode_complete"]
                self.current_state.done = True

            self.current_state.completion_score = self._completion_score(self.current_state)
            reward_detail = RewardSignal(
                score=grade.score,
                score_breakdown=grade.score_breakdown,
                matched=grade.matched,
                mistakes=grade.mistakes,
                partial_progress=grade.partial_progress,
                penalty_flags=grade.penalty_flags,
            )
            try:
                persist_step(self.current_state.episode_id, grade.reward, self.current_state.done, self.current_state.model_dump())
            except Exception:
                pass

            return StepResponse(
                observation=self._observation_from_state(self.current_state),
                state=deepcopy(self.current_state),
                reward=grade.reward,
                reward_detail=reward_detail,
                done=self.current_state.done,
                info=info,
            )
        except Exception as e:
            fallback_state = self.current_state or self.reset()
            return StepResponse(
                observation=self._observation_from_state(fallback_state),
                state=deepcopy(fallback_state),
                reward=0.01,
                reward_detail=RewardSignal(score=0.01),
                done=True,
                info={"error": str(e)},
            )

    def _observation_from_state(self, state: EnvironmentState) -> TriageObservation:
        return TriageObservation(
            environment_id=state.environment_id,
            episode_id=state.episode_id,
            task_id=state.task.task_id,
            difficulty=state.task.difficulty,
            step_count=state.step_count,
            max_steps=state.max_steps,
            current_turn=state.current_turn,
            turn_label=state.turn_label,
            email=deepcopy(state.email),
            thread_messages=deepcopy(state.thread_messages),
            pending_actions=list(state.pending_actions),
            sla_status=state.sla_status,
            escalation_level=state.escalation_level,
            human_review_required=state.human_review_required,
            done=state.done,
            history_length=len(state.history),
            completion_score=state.completion_score,
            queue_depth=state.queue_depth,
            pending_sla_breaches=state.pending_sla_breaches,
            reviewer_backlog=state.reviewer_backlog,
            customer_history_summary=state.customer_history_summary,
            business_impact=state.business_impact,
            suggested_departments=list(state.suggested_departments),
            ownership_status=state.ownership_status,
        )

    def _fallback_row(self) -> dict[str, object]:
        return {
            "email_id": "fallback-id",
            "thread_id": "fallback-thread",
            "subject": "System Warning: Dataset Connectivity Issue",
            "customer_name": "System Monitor",
            "customer_tier": "standard",
            "received_at": datetime.now(UTC).isoformat(),
            "sla_due_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            "email_text": "The environment is running in fallback mode because the dataset service is unavailable.",
            "category": "operations",
            "priority": "low",
            "department": "operations",
            "spam": 0,
            "sentiment": "neutral",
            "urgency": "low",
            "draft_response": "The triage system is currently experiencing technical difficulties with dataset access.",
            "escalation_required": 0,
        }

    def _completion_score(self, state: EnvironmentState) -> float:
        if not state.history:
            return 0.01
        matched_ratios = [
            sum(1 for value in (item.get("matched") or {}).values() if value) / max(len(item.get("matched") or {}), 1)
            for item in state.history
        ]
        base = sum(matched_ratios) / len(matched_ratios)
        feedback_bonus = min(len(state.human_feedback) * 0.03, 0.09)
        queue_bonus = 0.03 if state.queue_depth >= 30 and state.step_count > 0 else 0.0
        val = base + feedback_bonus + queue_bonus
        return round(min(max(val, 0.01), 0.99), 4)

    def _priority_max(self, left: str, right: str) -> str:
        return left if _PRIORITY_ORDER[left] >= _PRIORITY_ORDER[right] else right

    def _escalation_level(self, expected: dict[str, object]) -> str:
        priority = str(expected.get("priority", "low"))
        category = str(expected.get("category", "operations"))
        if priority == "critical" or category == "security":
            return "executive"
        if priority == "high" or bool(expected.get("human_review_required")):
            return "director"
        if priority == "medium":
            return "team_lead"
        return "none"

    def _ownership_status_from_action(self, action: AgentAction) -> str:
        if action.escalation or action.escalation_target in {"director", "executive"}:
            return "escalated"
        if action.assigned_owner and self.current_state and self.current_state.ownership_status == "assigned":
            return "reassigned"
        if action.assigned_owner:
            return "assigned"
        return self.current_state.ownership_status if self.current_state is not None else "unassigned"

    def _agent_thread_message(self, action: AgentAction, turn_label: str, episode_step: int) -> ThreadMessage:
        body = action.response_draft or action.internal_note or "Agent completed triage review."
        return ThreadMessage(
            message_id=f"agent-{episode_step:02d}",
            sender_role="agent",
            subject=f"Agent Response - {turn_label}",
            body=body,
            created_at=datetime.now(UTC).isoformat(),
            requires_response=False,
            tone="operational",
        )

    def _as_thread_message(self, email: EmailMessage, label: str, tone: str) -> ThreadMessage:
        return ThreadMessage(
            message_id=f"thread-{label.lower().replace(' ', '-')}-{email.email_id}",
            sender_role="customer",
            subject=email.subject,
            body=email.email_text,
            created_at=email.received_at,
            requires_response=True,
            tone=tone,
        )

    def _system_thread_message(self, subject: str, body: str) -> ThreadMessage:
        return ThreadMessage(
            message_id=f"system-{uuid4()}",
            sender_role="system",
            subject=subject,
            body=body,
            created_at=datetime.now(UTC).isoformat(),
            requires_response=False,
            tone="operational",
        )

    def _build_email(self, row: dict[str, object], *, suffix: str, body: str, received_at: str) -> EmailMessage:
        return EmailMessage(
            email_id=f"{row['email_id']}-{suffix}",
            thread_id=str(row["thread_id"]),
            subject=f"{suffix.replace('-', ' ').title()}: {row['subject']}",
            customer_name=str(row["customer_name"]),
            customer_tier=str(row["customer_tier"]),
            received_at=received_at,
            sla_due_at=str(row["sla_due_at"]),
            email_text=body,
        )

    def _owner_for_department(self, department: str, priority: str) -> str:
        prefix = {
            "finance_operations": "finops-billing-owner",
            "technical_support": "support-escalation-owner",
            "security_operations": "security-oncall-owner",
            "legal_operations": "legal-duty-owner",
            "people_operations": "hr-operations-owner",
            "revenue_operations": "sales-ops-owner",
            "partner_operations": "partner-success-owner",
            "operations": "ops-command-owner",
        }.get(department, "ops-command-owner")
        if priority == "critical":
            return f"{prefix}-p0"
        if priority == "high":
            return f"{prefix}-p1"
        return prefix

    def _eta_for_priority(self, priority: str) -> int:
        return {
            "critical": 2,
            "high": 6,
            "medium": 24,
            "low": 48,
        }.get(priority, 24)

    def _suggested_departments(self, category: str, department: str) -> list[str]:
        alternatives = {
            "billing": [department, "revenue_operations", "operations"],
            "technical_support": [department, "operations", "security_operations"],
            "sales": [department, "revenue_operations", "operations"],
            "legal": [department, "operations", "security_operations"],
            "human_resources": [department, "operations", "legal_operations"],
            "security": [department, "technical_support", "operations"],
            "operations": [department, "technical_support", "finance_operations"],
            "partnership": [department, "revenue_operations", "operations"],
        }
        return alternatives.get(category, [department, "operations"])

    def _customer_history_summary(self, row: dict[str, object]) -> str:
        tier = str(row["customer_tier"])
        priority = str(row["priority"])
        if tier == "strategic":
            return "Strategic account with prior escalations and low tolerance for missed commitments."
        if tier == "enterprise":
            return "Enterprise account with active renewal influence and expectation of named ownership."
        if priority in {"high", "critical"}:
            return "Recent complaint history suggests fast follow-up is expected to preserve trust."
        return "Standard account history with no recent escalations on record."

    def _business_impact(self, row: dict[str, object], priority: str | None = None) -> str:
        resolved_priority = priority or str(row["priority"])
        category = str(row["category"])
        tier = str(row["customer_tier"])
        if category == "security":
            return "Potential security exposure with leadership visibility and compliance risk."
        if resolved_priority == "critical":
            return "Direct operational disruption with revenue or contractual risk if ownership is delayed."
        if tier in {"enterprise", "strategic"}:
            return "High-value account impact with churn and renewal risk if communication stalls."
        return "Moderate operational impact that still requires timely coordination and customer updates."

    def _queue_context(self, row: dict[str, object], task, seed: int) -> dict[str, object]:
        base_priority = str(row["priority"])
        queue_depth = 8 + (seed % 11)
        if task.difficulty == "medium":
            queue_depth += 7
        if task.difficulty == "hard":
            queue_depth += 18
        if base_priority in {"high", "critical"}:
            queue_depth += 5
        pending_sla_breaches = max(0, (queue_depth // 8) - (0 if base_priority == "low" else 1))
        reviewer_backlog = 1 + (seed % 4) + (2 if task.difficulty == "hard" else 0)
        department = str(row["department"])
        return {
            "queue_depth": queue_depth,
            "pending_sla_breaches": pending_sla_breaches,
            "reviewer_backlog": reviewer_backlog,
            "customer_history_summary": self._customer_history_summary(row),
            "business_impact": self._business_impact(row),
            "suggested_departments": self._suggested_departments(str(row["category"]), department),
            "ownership_status": "unassigned",
        }

    def _build_expected(
        self,
        row: dict[str, object],
        *,
        priority: str,
        urgency: str,
        sentiment: str,
        human_review_required: bool,
        escalation_required: int,
        sla_status: str,
    ) -> dict[str, object]:
        department = str(row["department"])
        escalation_target = self._escalation_level(
            {
                "priority": priority,
                "category": row["category"],
                "human_review_required": human_review_required,
            }
        )
        return {
            "category": row["category"],
            "priority": priority,
            "department": department,
            "spam": int(row["spam"]),
            "sentiment": sentiment,
            "urgency": urgency,
            "response_draft": row["draft_response"],
            "escalation": bool(escalation_required),
            "escalation_required": escalation_required,
            "human_review_required": human_review_required,
            "request_human_review": human_review_required,
            "sla_status": sla_status,
            "assigned_owner": self._owner_for_department(department, priority),
            "resolution_eta_hours": self._eta_for_priority(priority),
            "customer_follow_up_required": int(row["spam"]) == 0,
            "escalation_target": escalation_target,
            "confidence": 0.95,
            "internal_note": "Executing standardized automated triage review.",
        }

    def _build_episode_plan(self, row: dict[str, object], task, queue_context: dict[str, object]) -> list[dict[str, object]]:
        base_email = EmailMessage(
            email_id=str(row["email_id"]),
            thread_id=str(row["thread_id"]),
            subject=str(row["subject"]),
            customer_name=str(row["customer_name"]),
            customer_tier=str(row["customer_tier"]),
            received_at=str(row["received_at"]),
            sla_due_at=str(row["sla_due_at"]),
            email_text=str(row["email_text"]),
        )
        base_priority = str(row["priority"])
        base_urgency = str(row["urgency"])
        base_sentiment = str(row["sentiment"])
        base_expected = self._build_expected(
            row,
            priority=base_priority,
            urgency=base_urgency,
            sentiment=base_sentiment,
            human_review_required=base_priority in {"high", "critical"} or str(row["category"]) in {"security", "legal"},
            escalation_required=int(row["escalation_required"]),
            sla_status="at_risk" if base_priority in {"high", "critical"} else "healthy",
        )
        plan = [
            {
                "label": "Initial Customer Email",
                "email": base_email,
                "expected": base_expected,
                "pending_actions": ["classify_email", "assign_priority", "route_department"],
                "thread_message": self._as_thread_message(base_email, "initial-customer-email", tone=base_sentiment),
                "context": queue_context,
            }
        ]

        if task.difficulty != "easy":
            plan[0]["thread_message"] = self._as_thread_message(base_email, "initial-customer-email", tone=base_sentiment)

        if not task.supports_threading or int(row["spam"]) == 1:
            return plan

        received_at = datetime.fromisoformat(str(row["received_at"]))
        follow_up_priority = self._priority_max(base_priority, "high")
        follow_up_urgency = self._priority_max(base_urgency, "high")
        follow_up_sentiment = "frustrated" if base_sentiment != "positive" else "neutral"
        follow_up_body = (
            f"Following up on {row['subject']}. We still do not have confirmation of ownership, and the issue is impacting stakeholders. "
            f"Please provide an immediate update before the SLA expires. Executive visibility is increasing for {row['customer_name']}."
        )
        follow_up_email = self._build_email(
            row,
            suffix="customer-follow-up",
            body=follow_up_body,
            received_at=(received_at + timedelta(hours=2)).isoformat(),
        )
        follow_up_expected = self._build_expected(
            row,
            priority=follow_up_priority,
            urgency=follow_up_urgency,
            sentiment=follow_up_sentiment,
            human_review_required=True,
            escalation_required=1 if follow_up_priority in {"high", "critical"} else int(row["escalation_required"]),
            sla_status="at_risk",
        )
        follow_up_context = {
            **queue_context,
            "queue_depth": int(queue_context["queue_depth"]) + 6,
            "pending_sla_breaches": int(queue_context["pending_sla_breaches"]) + 1,
            "reviewer_backlog": int(queue_context["reviewer_backlog"]) + 1,
            "business_impact": self._business_impact(row, priority=follow_up_priority),
            "ownership_status": "assigned",
        }
        plan.append(
            {
                "label": "Customer Follow-up",
                "email": follow_up_email,
                "expected": follow_up_expected,
                "pending_actions": ["reassess_priority", "assign_owner", "update_routing", "send_follow_up_response"],
                "thread_message": self._as_thread_message(follow_up_email, "customer-follow-up", tone=follow_up_sentiment),
                "context": follow_up_context,
            }
        )

        executive_priority = self._priority_max(follow_up_priority, "critical") if str(row["customer_tier"]) in {"enterprise", "strategic"} or str(row["category"]) in {"security", "legal"} else follow_up_priority
        executive_urgency = self._priority_max(follow_up_urgency, "critical") if executive_priority == "critical" else follow_up_urgency
        executive_body = (
            f"Leadership escalation for thread {row['thread_id']}: provide final routing, owner accountability, and executive-safe messaging. "
            f"Customer tier is {row['customer_tier']} and the current issue remains unresolved."
        )
        executive_email = self._build_email(
            row,
            suffix="executive-escalation",
            body=executive_body,
            received_at=(received_at + timedelta(hours=4)).isoformat(),
        )
        executive_expected = self._build_expected(
            row,
            priority=executive_priority,
            urgency=executive_urgency,
            sentiment="frustrated",
            human_review_required=True,
            escalation_required=1,
            sla_status="breached" if executive_priority == "critical" else "at_risk",
        )
        executive_context = {
            **follow_up_context,
            "queue_depth": int(follow_up_context["queue_depth"]) + 4,
            "pending_sla_breaches": int(follow_up_context["pending_sla_breaches"]) + 1,
            "reviewer_backlog": int(follow_up_context["reviewer_backlog"]) + 2,
            "business_impact": self._business_impact(row, priority=executive_priority),
            "ownership_status": "escalated",
        }
        plan.append(
            {
                "label": "Executive Escalation",
                "email": executive_email,
                "expected": executive_expected,
                "pending_actions": ["request_human_review", "escalate_case", "assign_final_owner", "finalize_response_plan"],
                "thread_message": self._as_thread_message(executive_email, "executive-escalation", tone="frustrated"),
                "context": executive_context,
            }
        )
        return plan
