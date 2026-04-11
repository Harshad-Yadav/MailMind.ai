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
    # 0. STRICT VALIDATOR CONFIGURATION (Exactly as requested by instructions)
    print("[*] Accessing environment variables...", flush=True)
    base_url = os.environ.get("API_BASE_URL")
    api_key = os.environ.get("API_KEY")
    model_name = os.getenv("MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
    
    if not base_url or not api_key:
        print(f"[ERROR] Required variables missing. Base: {base_url}, Key: {'present' if api_key else 'missing'}", flush=True)

    # Use exact values from environment if possible, to avoid normalization errors
    client = OpenAI(base_url=base_url, api_key=api_key)
    rewards = []
    steps_taken = 0
    success = False
    
    log_start(task=TASK_ID, env=BENCHMARK, model=model_name)
    
    try:
        # Pre-flight call with generic model fallback to ensure proxy observation
        print("[*] Connectivity test to proxy...", flush=True)
        try:
            client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": "ping"}],
                max_tokens=1
            )
            print("[+] Connectivity successful.", flush=True)
        except Exception as e:
            print(f"[!] Connectivity test failed with model {model_name}: {e}", flush=True)
            # Try once more with a common model slug just in case the name is the issue
            try:
                print("[*] Retrying with generic model name...", flush=True)
                client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "ping"}],
                    max_tokens=1
                )
                print("[+] Connectivity successful with fallback model.", flush=True)
            except:
                print("[!] All connectivity tests failed. Proceeding to environment loop anyway.", flush=True)

        # 1. Wait for environment
        print(f"[*] Waiting for local environment at {ENV_URL}...", flush=True)
        env_ready = await wait_for_env(timeout=300)
        if not env_ready:
            print("[!] Environment wait timed out. Continuing with attempted reset.", flush=True)
            
        async with httpx.AsyncClient(timeout=60.0) as http:
            # 2. Reset
            print(f"[*] Attempting reset for task: {TASK_ID}", flush=True)
            try:
                resp = await http.post(f"{ENV_URL}/reset", params={"task_id": TASK_ID})
                if resp.status_code != 200: 
                    print(f"[ERROR] Reset failed ({resp.status_code}): {resp.text}", flush=True)
                    # We continue to log_end to avoid unhandled exception error
                data = resp.json()
                obs = data.get("observation", {})
            except Exception as e:
                print(f"[ERROR] Reset exception: {e}", flush=True)
                obs = {}
            
            for step in range(1, MAX_STEPS + 1):
                if not obs or obs.get("done"): break
                
                # 3. LLM call via Proxy
                prompt = build_prompt(obs)
                try:
                    print(f"[*] Step {step}: Requesting completion...", flush=True)
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are a professional email triage agent. Output JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0,
                    )
                    raw_action = completion.choices[0].message.content or "{}"
                    action_dict = safe_parse_json(raw_action)
                except Exception as e:
                    print(f"[ERROR] LLM call failed: {e}", flush=True)
                    action_dict = {"internal_note": f"Inference failed: {e}"}
                
                # 4. Environment Step
                try:
                    step_resp = await http.post(f"{ENV_URL}/step", json={"action": action_dict})
                    if step_resp.status_code != 200:
                        print(f"[ERROR] Step failed: {step_resp.text}", flush=True)
                        log_step(step, "error", 0.0, True, f"Status: {step_resp.status_code}")
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
                except Exception as e:
                    print(f"[ERROR] Step exception: {e}", flush=True)
                    log_step(step, "exception", 0.0, True, str(e))
                    break
                
            # Final Score Calculation
            score = obs.get("completion_score", 0.01) if obs else 0.01
            score = max(0.01, min(0.99, float(score)))
            success = score >= 0.7 
            
    except Exception as e:
        print(f"[FATAL] Global inference error: {e}", flush=True)
        if steps_taken == 0:
            log_step( step=1, action="error", reward=0.01, done=True, error=str(e))
            steps_taken = 1
            rewards = [0.01]
    finally:
        if 'score' not in locals():
            raw = sum(rewards) / len(rewards) if rewards else 0.01
            score = max(0.01, min(0.99, float(raw)))
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())
