import asyncio
import os
import json
import time
import textwrap
from typing import List, Optional, Any
import httpx
from openai import OpenAI

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
TASK_ID = os.getenv("TASK_ID", "task-full-enterprise-hard")
MAX_STEPS = 5
BENCHMARK = "advanced-email-triage"

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

def safe_parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1: return {}
    try: return json.loads(text[start:end+1])
    except: return {}

async def wait_for_env(timeout=30):
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                resp = await client.get(f"{ENV_URL}/health")
                if resp.status_code == 200: return True
            except: pass
            await asyncio.sleep(1)
    return False

def build_prompt(obs: dict) -> str:
    email = obs.get("email", {})
    messages = obs.get("thread_messages", [])
    thread_text = "\n".join([f"[{m['sender_role']}] {m['body'][:200]}" for m in messages[-3:]])
    
    return textwrap.dedent(f"""
        Task: Triage this enterprise email.
        Subject: {email.get('subject')}
        Body: {email.get('email_text')}
        Thread Context:
        {thread_text}
        
        Return JSON with: category, priority, department, spam(0|1), sentiment, urgency, response_draft, escalation(bool), confidence(0-1), internal_note, request_human_review(bool), assigned_owner, resolution_eta_hours(int), customer_follow_up_required(bool), escalation_target(none|team_lead|director|executive).
    """).strip()

async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    rewards = []
    steps_taken = 0
    success = False
    
    log_start(task=TASK_ID, env=BENCHMARK, model=MODEL_NAME)
    
    try:
        # 1. Wait for environment
        if not await wait_for_env():
            raise Exception("Environment timed out")
            
        async with httpx.AsyncClient(timeout=30.0) as http:
            # 2. Reset
            resp = await http.post(f"{ENV_URL}/reset", params={"task_id": TASK_ID})
            if resp.status_code != 200: raise Exception(f"Reset failed: {resp.text}")
            data = resp.json()
            obs = data["observation"]
            
            for step in range(1, MAX_STEPS + 1):
                if obs.get("done"): break
                
                # 3. LLM call
                prompt = build_prompt(obs)
                try:
                    completion = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "You are a professional email triage JSON agent. Return ONLY JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0,
                    )
                    raw_action = completion.choices[0].message.content or "{}"
                    action_dict = safe_parse_json(raw_action)
                except Exception as e:
                    action_dict = {"internal_note": f"LLM Error: {str(e)}"}
                
                # 4. Step
                step_resp = await http.post(f"{ENV_URL}/step", json={"action": action_dict})
                if step_resp.status_code != 200:
                    log_step(step, "error", 0.0, True, f"Step Failed: {step_resp.text}")
                    break
                    
                result = step_resp.json()
                reward = float(result.get("reward", 0.0))
                done = result.get("done", False)
                obs = result.get("observation", {})
                
                rewards.append(reward)
                steps_taken = step
                
                action_str = f"cat={action_dict.get('category','?')},pri={action_dict.get('priority','?')}"
                log_step(step, action_str, reward, done, None)
                
                if done: break
                
            # Final Score Calculation
            score = obs.get("completion_score", 0.0)
            success = score >= 0.7 # Example threshold
            
    except Exception as e:
        # Ensure we at least emit one fallback step if it crashed early
        if steps_taken == 0:
            log_step(1, "fallback", 0.0, True, str(e))
            steps_taken = 1
            rewards = [0.0]
    finally:
        # If we didn't get a score from obs, fallback to rewards mean
        if 'score' not in locals():
            score = sum(rewards) / len(rewards) if rewards else 0.0
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())
