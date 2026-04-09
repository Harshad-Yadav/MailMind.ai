import asyncio
import os
import json
import time
import textwrap
import sys
from typing import List, Optional, Any
import httpx
from openai import OpenAI

# Configuration
TASK_ID = os.getenv("TASK_ID", "task-full-enterprise-hard")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
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

async def wait_for_env(timeout=300):
    print(f"[*] Waiting for environment at {ENV_URL} (timeout={timeout}s)...", flush=True)
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                resp = await client.get(f"{ENV_URL}/health")
                if resp.status_code == 200:
                    print(f"[+] Environment is healthy after {int(time.time() - start_time)}s", flush=True)
                    return True
            except: pass
            await asyncio.sleep(2)
    return False

def build_prompt(obs: dict) -> str:
    email = obs.get("email", {})
    messages = obs.get("thread_messages", [])
    thread_text = "\n".join([f"[{m['sender_role']}] {m['body'][:200]}" for m in messages[-3:]])
    
    return textwrap.dedent(f"""
        Task: Triage this enterprise email according to OpenEnv criteria.
        Subject: {email.get('subject')}
        Body: {email.get('email_text')}
        Thread Context:
        {thread_text}
        
        Return JSON with: category, priority, department, spam(0|1), sentiment, urgency, response_draft, escalation(bool), confidence(0-1), internal_note, request_human_review(bool), assigned_owner, resolution_eta_hours(int), customer_follow_up_required(bool), escalation_target(none|team_lead|director|executive).
    """).strip()

async def main():
    # 0. STRICT VALIDATOR CONFIGURATION (os.environ as required by Hackathon rules)
    try:
        raw_base_url = os.environ["API_BASE_URL"]
        api_key = os.environ["API_KEY"]
        model_name = os.getenv("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
    except KeyError as e:
        print(f"[CRITICAL] Required environment variable MISSING: {e}", flush=True)
        sys.exit(1)

    # Normalize Base URL: Strip trailing slash and ensure /v1 suffix for openai-python compatibility
    base_url = raw_base_url.rstrip("/")
    if not base_url.endswith("/v1") and "googleapis.com" not in base_url:
        base_url = f"{base_url}/v1"
    
    print(f"[*] Initializing OpenAI Client (Base: {base_url})", flush=True)
    client = OpenAI(base_url=base_url, api_key=api_key)

    # 1. PRE-FLIGHT CONNECTIVITY TEST (Ensures the proxy observes at least one call immediately)
    print("[*] Performing proxy connectivity test...", flush=True)
    try:
        client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": "ping"}],
            max_tokens=1
        )
        print("[+] Proxy connectivity test successful.", flush=True)
    except Exception as e:
        print(f"[CRITICAL] LLM Proxy communication FAILED: {e}", flush=True)
        # We fail loudly here to prevent a "dummy" run that passes Phase 2 logic but misses calls
        sys.exit(1)

    rewards = []
    steps_taken = 0
    success = False
    
    log_start(task=TASK_ID, env=BENCHMARK, model=model_name)
    
    try:
        # 2. Wait for environment
        if not await wait_for_env(timeout=300):
            print("[CRITICAL] Environment timed out.", flush=True)
            sys.exit(1)
            
        async with httpx.AsyncClient(timeout=60.0) as http:
            # 3. Reset
            print(f"[*] Resetting environment for task: {TASK_ID}", flush=True)
            resp = await http.post(f"{ENV_URL}/reset", params={"task_id": TASK_ID})
            if resp.status_code != 200: 
                print(f"[CRITICAL] Reset failed: {resp.text}", flush=True)
                sys.exit(1)
            
            data = resp.json()
            obs = data["observation"]
            
            for step in range(1, MAX_STEPS + 1):
                if obs.get("done"): 
                    print(f"[*] Episode finished naturally at step {step-1}", flush=True)
                    break
                
                # 4. LLM call via Proxy
                prompt = build_prompt(obs)
                try:
                    print(f"[*] Step {step}: Requesting completion from proxy...", flush=True)
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are an enterprise email triage agent. Output ONLY strict JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0,
                    )
                    raw_action = completion.choices[0].message.content or "{}"
                    action_dict = safe_parse_json(raw_action)
                except Exception as e:
                    print(f"[!] LLM call failed: {e}", flush=True)
                    action_dict = {"internal_note": f"Call failed: {e}"}
                
                # 5. Environment Step
                step_resp = await http.post(f"{ENV_URL}/step", json={"action": action_dict})
                if step_resp.status_code != 200:
                    print(f"[!] Env step failed: {step_resp.text}", flush=True)
                    log_step(step, "error", 0.0, True, f"Error: {step_resp.status_code}")
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
            success = score >= 0.7 
            
    except Exception as e:
        print(f"[FATAL] Inference loop error: {e}", flush=True)
        if steps_taken == 0:
            log_step(1, "error", 0.0, True, str(e))
            steps_taken = 1
            rewards = [0.0]
    finally:
        if 'score' not in locals():
            score = sum(rewards) / len(rewards) if rewards else 0.0
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())
