from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any

from backend.schemas.env import AgentAction, TriageObservation

# Defaults based on Hackathon rules
DEFAULT_API_BASE = "https://router.huggingface.co/v1"
DEFAULT_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run inference using Hugging Face Router.")
    parser.add_argument("--model", default=os.getenv("MODEL_NAME", DEFAULT_MODEL), help="Model Name")
    parser.add_argument("--base-url", default=os.getenv("API_BASE_URL", DEFAULT_API_BASE), help="API Base URL")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--max-steps", type=int, default=5, help="Max steps per episode")
    parser.add_argument("--task-id", type=str, default="task-full-enterprise-hard", help="Task ID to run")
    return parser.parse_args()

def safe_parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
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

def coerce_bool(value: Any) -> bool:
    if isinstance(value, bool): return value
    if isinstance(value, (int, float)): return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}

def fallback_action() -> AgentAction:
    return AgentAction(
        category="operations",
        priority="medium",
        department="operations",
        spam=0,
        sentiment="neutral",
        urgency="medium",
        response_draft="We are reviewing your request.",
        escalation=False,
        confidence=0.5,
        internal_note="Fallback action triggered due to parse failure.",
        request_human_review=False,
        assigned_owner="ops-command-owner",
        resolution_eta_hours=24,
        customer_follow_up_required=True,
        escalation_target="none"
    )

def parse_and_normalize(action_dict: dict[str, Any]) -> AgentAction:
    if not action_dict:
        return fallback_action()
    
    normalized = {
        "category": str(action_dict.get("category", "operations")).strip().lower(),
        "priority": str(action_dict.get("priority", "medium")).strip().lower(),
        "department": str(action_dict.get("department", "operations")).strip().lower(),
        "spam": 1 if str(action_dict.get("spam", 0)).strip().lower() in {"1", "true", "yes"} else 0,
        "sentiment": str(action_dict.get("sentiment", "neutral")).strip().lower(),
        "urgency": str(action_dict.get("urgency", "medium")).strip().lower(),
        "response_draft": str(action_dict.get("response_draft", "We are reviewing your request.")).strip(),
        "escalation": coerce_bool(action_dict.get("escalation", False)),
        "internal_note": str(action_dict.get("internal_note", "Triage completed.")).strip(),
        "request_human_review": coerce_bool(action_dict.get("request_human_review", False)),
        "assigned_owner": str(action_dict.get("assigned_owner", "ops-command-owner")).strip().lower(),
        "customer_follow_up_required": coerce_bool(action_dict.get("customer_follow_up_required", True)),
        "escalation_target": str(action_dict.get("escalation_target", "none")).strip().lower(),
    }
    try:
        normalized["confidence"] = max(0.0, min(1.0, float(action_dict.get("confidence", 0.65))))
    except (TypeError, ValueError):
        normalized["confidence"] = 0.65

    try:
        normalized["resolution_eta_hours"] = max(0, min(168, int(action_dict.get("resolution_eta_hours", 24))))
    except (TypeError, ValueError):
        normalized["resolution_eta_hours"] = 24

    return AgentAction(**normalized)

def build_prompt(observation: TriageObservation) -> str:
    thread_excerpt = "\n\n".join(
        f"[{m.sender_role}] {m.subject}\n{m.body}" for m in observation.thread_messages[-4:]
    )
    return (
        f"Task Target: Process the email triage operation.\n"
        f"Current Turn: {observation.current_turn}/{observation.max_steps}\n"
        f"Subject: {observation.email.subject}\n"
        f"Customer: {observation.email.customer_name}\n"
        f"Email Body:\n{observation.email.email_text}\n\n"
        f"Thread Context:\n{thread_excerpt}\n\n"
        "Return a JSON object with exactly these keys: "
        "category, priority, department, spam, sentiment, urgency, response_draft, escalation, confidence, internal_note, request_human_review, assigned_owner, resolution_eta_hours, customer_follow_up_required, escalation_target. "
        "Use lowercase enum-like strings where appropriate, spam must be 0 or 1, escalation and request_human_review must be booleans, customer_follow_up_required must be boolean, resolution_eta_hours must be an integer, and confidence must be between 0 and 1."
    )

def main() -> None:
    args = parse_args()

    # Robust HF_TOKEN handling
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("[WARN] HF_TOKEN missing, using fallback mode")
        hf_token = "dummy"

    # Deferred import for OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(base_url=args.base_url, api_key=hf_token)
    except Exception as e:
        print(f"[ERROR] OpenAI client init failed: {e}")
        client = None

    # [START] task=<task_name> env=<benchmark> model=<model_name>
    print(f"[START] task={args.task_id} env=advanced-email-triage model={args.model}")
    
    rewards: list[float] = []
    success = False
    step_count = 0
    last_error = "null"
    fallback_mode = False

    try:
        try:
            from backend.services.env_service import OpenEnvEmailTriageEnvironment
            env = OpenEnvEmailTriageEnvironment()
            env.reset(task_id=args.task_id, seed=args.seed)
        except Exception as e:
            print(f"[ERROR] Env init failed: {e}")
            fallback_mode = True

        done = False
        while not done and step_count < args.max_steps:
            if fallback_mode:
                step_count += 1
                reward = 0.0
                rewards.append(reward)
                done = True
                print(f"[STEP] step={step_count} action=\"fallback=true\" reward={reward:.2f} done={str(done).lower()} error=env_unavailable")
                break

            try:
                observation = env.observation()
            except Exception as e:
                print(f"[ERROR] Observation failed: {e}")
                observation = None

            if observation is None:
                step_count += 1
                reward = 0.0
                rewards.append(reward)
                done = True
                print(f"[STEP] step={step_count} action=\"fallback=true\" reward={reward:.2f} done={str(done).lower()} error=observation_failed")
                break

            prompt = build_prompt(observation)
            
            try:
                if client:
                    response = client.chat.completions.create(
                        model=args.model,
                        temperature=0.0,
                        seed=args.seed,
                        max_tokens=600,
                        messages=[
                            {"role": "system", "content": "You are an enterprise email triage agent. Return only strict JSON. No conversational text."},
                            {"role": "user", "content": prompt},
                        ]
                    )
                    output = response.choices[0].message.content or "{}"
                    last_error = "null"
                else:
                    output = "{}"
                    last_error = "client_unavailable"
            except Exception as e:
                output = "{}"
                last_error = str(e)
            
            parsed = safe_parse_json(output)
            action = parse_and_normalize(parsed)
            
            try:
                result = env.step(action)
                reward = float(result.reward)
                done = result.done
                success = result.state.completion_score >= 0.8
                last_error = "null"
            except Exception as e:
                print(f"[ERROR] Env step failed: {e}")
                reward = 0.0
                done = True
                last_error = str(e)
            
            step_count += 1
            rewards.append(reward)
            
            action_str = f"category={action.category},priority={action.priority},dept={action.department}"
            print(f"[STEP] step={step_count} action=\"{action_str}\" reward={reward:.2f} done={str(done).lower()} error={last_error}")
            
            if not done:
                time.sleep(0.5)

    except Exception as e:
        last_error = str(e)
        if step_count == 0:
            step_count = 1
            rewards.append(0.0)
            print(f"[STEP] step=1 action=\"fallback=true\" reward=0.00 done=true error={last_error}")
        
    if not rewards:
        rewards.append(0.0)
        step_count = max(step_count, 1)

    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={step_count} rewards={rewards_str}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[END] success=false steps=0 rewards=0.00 error={str(e)}")
