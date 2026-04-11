from __future__ import annotations

from typing import Any

from backend.schemas.env import AgentAction, GraderResponse, TaskDefinition

_ESCALATION_ORDER = {"none": 0, "team_lead": 1, "director": 2, "executive": 3}


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _response_quality_score(action: AgentAction, expected: dict[str, Any], weight: float) -> tuple[float, bool, str | None]:
    draft = (action.response_draft or "").strip().lower()
    if not draft:
        return 0.0, False, "response draft is empty"

    signals = 0
    total_signals = 3
    if len(draft) >= 32:
        signals += 1
    if any(token in draft for token in ["review", "update", "assigned", "team", "investigat", "sla", "priority", "route"]):
        signals += 1
    if any(token in draft for token in ["owner", "eta", "next step", "follow up", "escalat"]):
        signals += 1
    if expected.get("spam") == 1:
        total_signals += 1
        if "spam" in draft or "unsolicited" in draft:
            signals += 1

    earned = round(weight * (signals / total_signals), 4)
    matched = earned >= round(weight * 0.6, 4)
    issue = None if matched else "response draft lacks enough operational detail"
    return earned, matched, issue


def _add_component(
    components: list[dict[str, Any]],
    *,
    name: str,
    weight: float,
    earned: float,
    matched: bool,
    mistake: str | None = None,
    penalty_flag: str | None = None,
) -> None:
    components.append(
        {
            "name": name,
            "weight": weight,
            "earned": max(0.0, min(weight, round(earned, 4))),
            "matched": matched,
            "mistake": mistake,
            "penalty_flag": penalty_flag if not matched else None,
        }
    )


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def grade_action(task: TaskDefinition, action: AgentAction, expected: dict[str, Any]) -> GraderResponse:
    action_payload = action.model_dump()
    matched: dict[str, bool] = {}
    mistakes: list[str] = []
    penalty_flags: list[str] = []
    components: list[dict[str, Any]] = []

    for field in task.required_outputs:
        predicted = action_payload.get(field)
        actual = expected.get(field)
        if field == "response_draft":
            is_match = isinstance(predicted, str) and len(predicted.strip()) >= 24
        elif field == "escalation":
            is_match = bool(predicted) == bool(expected.get("escalation_required"))
        else:
            is_match = _normalize(predicted) == _normalize(actual)

        matched[field] = is_match
        weight = task.reward_weights.get(field, 0.0)
        _add_component(
            components,
            name=field,
            weight=weight,
            earned=weight if is_match else 0.0,
            matched=is_match,
            mistake=None if is_match else f"{field} expected {actual!r} but received {predicted!r}",
            penalty_flag=f"incorrect_{field}" if not is_match else None,
        )
        if not is_match:
            mistakes.append(f"{field} expected {actual!r} but received {predicted!r}")

    if task.difficulty != "easy":
        expected_urgency = _normalize(expected.get("urgency"))
        priority = _normalize(action_payload.get("priority"))
        sla_weight = 0.08
        sla_match = not (expected_urgency in {"high", "critical"} and priority not in {"high", "critical"})
        matched["sla_priority_alignment"] = sla_match
        _add_component(
            components,
            name="sla_priority_alignment",
            weight=sla_weight,
            earned=sla_weight if sla_match else 0.0,
            matched=sla_match,
            mistake=None if sla_match else "urgent email was not assigned sufficiently high priority",
            penalty_flag="urgent_email_underprioritized",
        )
        if not sla_match:
            mistakes.append("urgent email was not assigned sufficiently high priority")
            penalty_flags.append("urgent_email_underprioritized")

    if "spam" in task.required_outputs:
        spam_weight = 0.08 if task.difficulty == "hard" or expected.get("spam") == 1 else 0.04
        spam_match = not (expected.get("spam") == 1 and action_payload.get("spam") != 1)
        matched["spam_guardrail"] = spam_match
        _add_component(
            components,
            name="spam_guardrail",
            weight=spam_weight,
            earned=spam_weight if spam_match else 0.0,
            matched=spam_match,
            mistake=None if spam_match else "spam email was not marked as spam",
            penalty_flag="spam_not_flagged",
        )
        if not spam_match:
            mistakes.append("spam email was not marked as spam")
            penalty_flags.append("spam_not_flagged")

    if task.difficulty == "hard":
        response_weight = 0.08
        quality_earned, quality_match, quality_issue = _response_quality_score(action, expected, response_weight)
        matched["response_quality"] = quality_match
        _add_component(
            components,
            name="response_quality",
            weight=response_weight,
            earned=quality_earned,
            matched=quality_match,
            mistake=quality_issue,
            penalty_flag="weak_response_draft",
        )
        if quality_issue:
            mistakes.append(quality_issue)
            penalty_flags.append("weak_response_draft")

        human_review_required = bool(expected.get("human_review_required"))
        review_requested = bool(action.request_human_review)
        review_weight = 0.08
        if human_review_required and review_requested:
            review_earned = review_weight
            review_match = True
            review_issue = None
        elif human_review_required and not review_requested:
            review_earned = 0.0
            review_match = False
            review_issue = "high-risk turn required human review but none was requested"
        elif review_requested:
            review_earned = round(review_weight * 0.75, 4)
            review_match = True
            review_issue = None
        else:
            review_earned = round(review_weight * 0.5, 4)
            review_match = True
            review_issue = None
        matched["human_review"] = review_match
        _add_component(
            components,
            name="human_review",
            weight=review_weight,
            earned=review_earned,
            matched=review_match,
            mistake=review_issue,
            penalty_flag="missed_human_review",
        )
        if review_issue:
            mistakes.append(review_issue)
            penalty_flags.append("missed_human_review")

        confidence = action.confidence
        confidence_weight = 0.04
        if confidence is None:
            confidence_earned = round(confidence_weight * 0.25, 4)
            confidence_match = False
            confidence_issue = "confidence score was omitted"
            confidence_flag = "missing_confidence"
        elif human_review_required and confidence > 0.85 and not review_requested:
            confidence_earned = 0.0
            confidence_match = False
            confidence_issue = "confidence was too high for a risky turn without review"
            confidence_flag = "overconfident_without_review"
        elif human_review_required and review_requested and confidence <= 0.85:
            confidence_earned = confidence_weight
            confidence_match = True
            confidence_issue = None
            confidence_flag = None
        elif not human_review_required and confidence >= 0.6:
            confidence_earned = confidence_weight
            confidence_match = True
            confidence_issue = None
            confidence_flag = None
        else:
            confidence_earned = round(confidence_weight * 0.5, 4)
            confidence_match = True
            confidence_issue = None
            confidence_flag = None
        matched["confidence_calibration"] = confidence_match
        _add_component(
            components,
            name="confidence_calibration",
            weight=confidence_weight,
            earned=confidence_earned,
            matched=confidence_match,
            mistake=confidence_issue,
            penalty_flag=confidence_flag,
        )
        if confidence_issue:
            mistakes.append(confidence_issue)
            if confidence_flag:
                penalty_flags.append(confidence_flag)

        note_weight = 0.04
        has_note = bool((action.internal_note or "").strip())
        matched["internal_note"] = has_note
        _add_component(
            components,
            name="internal_note",
            weight=note_weight,
            earned=note_weight if has_note else 0.0,
            matched=has_note,
            mistake=None if has_note else "hard-task action omitted an internal triage note",
            penalty_flag="missing_internal_note",
        )
        if not has_note:
            mistakes.append("hard-task action omitted an internal triage note")
            penalty_flags.append("missing_internal_note")

        owner_weight = 0.05
        expected_owner = str(expected.get("assigned_owner", "")).strip().lower()
        predicted_owner = str(action.assigned_owner or "").strip().lower()
        owner_present = bool(predicted_owner)
        owner_match = owner_present and (not expected_owner or predicted_owner == expected_owner)
        matched["ownership_assignment"] = owner_match
        _add_component(
            components,
            name="ownership_assignment",
            weight=owner_weight,
            earned=owner_weight if owner_match else (round(owner_weight * 0.5, 4) if owner_present else 0.0),
            matched=owner_match,
            mistake=None if owner_match else "case owner was missing or did not match the expected owning team",
            penalty_flag="missing_owner_assignment",
        )
        if not owner_match:
            mistakes.append("case owner was missing or did not match the expected owning team")
            penalty_flags.append("missing_owner_assignment")

        eta_weight = 0.05
        expected_eta = expected.get("resolution_eta_hours")
        predicted_eta = action.resolution_eta_hours
        if predicted_eta is None:
            eta_earned = 0.0
            eta_match = False
            eta_issue = "resolution ETA was omitted"
            eta_flag = "missing_eta"
        else:
            max_eta = int(expected_eta) if expected_eta is not None else 24
            if predicted_eta <= max_eta:
                eta_earned = eta_weight
                eta_match = True
                eta_issue = None
                eta_flag = None
            elif predicted_eta <= max_eta * 2:
                eta_earned = round(eta_weight * 0.5, 4)
                eta_match = True
                eta_issue = None
                eta_flag = None
            else:
                eta_earned = 0.0
                eta_match = False
                eta_issue = f"resolution ETA was too slow for the case severity; expected <= {max_eta} hours"
                eta_flag = "eta_misaligned_with_sla"
        matched["resolution_eta"] = eta_match
        _add_component(
            components,
            name="resolution_eta",
            weight=eta_weight,
            earned=eta_earned,
            matched=eta_match,
            mistake=eta_issue,
            penalty_flag=eta_flag,
        )
        if eta_issue:
            mistakes.append(eta_issue)
            if eta_flag:
                penalty_flags.append(eta_flag)

        follow_up_weight = 0.04
        expected_follow_up = _coerce_bool(expected.get("customer_follow_up_required", True))
        follow_up_match = bool(action.customer_follow_up_required) == expected_follow_up
        matched["customer_follow_up"] = follow_up_match
        _add_component(
            components,
            name="customer_follow_up",
            weight=follow_up_weight,
            earned=follow_up_weight if follow_up_match else 0.0,
            matched=follow_up_match,
            mistake=None if follow_up_match else "customer follow-up commitment did not match case expectations",
            penalty_flag="follow_up_missed",
        )
        if not follow_up_match:
            mistakes.append("customer follow-up commitment did not match case expectations")
            penalty_flags.append("follow_up_missed")

        escalation_weight = 0.05
        expected_target = str(expected.get("escalation_target", "none")).strip().lower() or "none"
        predicted_target = str(action.escalation_target or "none").strip().lower()
        expected_rank = _ESCALATION_ORDER.get(expected_target, 0)
        predicted_rank = _ESCALATION_ORDER.get(predicted_target, 0)
        if predicted_target == expected_target:
            escalation_earned = escalation_weight
            escalation_match = True
            escalation_issue = None
            escalation_flag = None
        elif 0 <= predicted_rank - expected_rank <= 1:
            escalation_earned = round(escalation_weight * 0.5, 4)
            escalation_match = True
            escalation_issue = None
            escalation_flag = None
        else:
            escalation_earned = 0.0
            escalation_match = False
            if predicted_rank < expected_rank:
                escalation_issue = f"escalation target was too low; expected {expected_target}"
                escalation_flag = "under_escalated"
            else:
                escalation_issue = f"escalation target was too high; expected {expected_target}"
                escalation_flag = "over_escalated"
        matched["escalation_target"] = escalation_match
        _add_component(
            components,
            name="escalation_target",
            weight=escalation_weight,
            earned=escalation_earned,
            matched=escalation_match,
            mistake=escalation_issue,
            penalty_flag=escalation_flag,
        )
        if escalation_issue:
            mistakes.append(escalation_issue)
            if escalation_flag:
                penalty_flags.append(escalation_flag)

    total_possible = round(sum(component["weight"] for component in components), 4)
    total_earned = round(sum(component["earned"] for component in components), 4)
    base_score = round(total_earned / total_possible, 4) if total_possible else 0.0
    penalty_deduction = len(set(penalty_flags)) * 0.1
    
    # Enforce standard OpenEnv bounds of [0.0, 1.0] inclusively.
    # The score directly affects Phase 2 verification checks testing for perfect 1.0 actions.
    raw_score = max(0.0, min(1.0, round(base_score - penalty_deduction, 4)))
    score = raw_score
    
    # Ensure reward follows the score accurately without compression
    reward = score
    
    partial_progress = round(
        sum(1 for value in matched.values() if value) / max(len(matched), 1),
        4,
    )
    score_breakdown = {
        component["name"]: round(component["earned"] / total_possible, 4) if total_possible else 0.0
        for component in components
    }

    return GraderResponse(
        score=score,
        reward=score,
        score_breakdown=score_breakdown,
        mistakes=mistakes,
        matched=matched,
        partial_progress=partial_progress,
        penalty_flags=sorted(set(penalty_flags)),
    )
