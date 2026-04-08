from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.main import app


def run_command(command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output


def check_openenv_validate() -> tuple[bool, str]:
    return run_command([sys.executable, "-m", "openenv.cli", "validate"])


def check_api() -> tuple[bool, str]:
    client = TestClient(app)
    reset = client.post("/reset", params={"task_id": "task-full-enterprise-hard", "seed": 42})
    if reset.status_code != 200:
        return False, f"/reset failed with status {reset.status_code}"
    step = client.post(
        "/step",
        json={
            "action": {
                "category": "security",
                "priority": "critical",
                "department": "security_operations",
                "spam": 0,
                "sentiment": "frustrated",
                "urgency": "critical",
                "response_draft": "We assigned the security owner, escalated this to leadership, and will follow up within 2 hours.",
                "escalation": True,
                "confidence": 0.81,
                "internal_note": "Security leadership notified.",
                "request_human_review": True,
                "assigned_owner": "security-oncall-owner-p0",
                "resolution_eta_hours": 2,
                "customer_follow_up_required": True,
                "escalation_target": "executive",
            }
        },
    )
    if step.status_code != 200:
        return False, f"/step failed with status {step.status_code}"
    payload = step.json()
    return True, json.dumps(
        {
            "reward": payload["reward"],
            "done": payload["done"],
            "matched_keys": sorted(payload["reward_detail"]["matched"].keys())[:5],
        }
    )


def check_docker_available() -> tuple[bool, str]:
    docker_path = shutil.which("docker")
    if not docker_path:
        return False, "docker command not found in PATH"
    return True, docker_path


def main() -> None:
    checks = [
        ("openenv validate", check_openenv_validate),
        ("api smoke test", check_api),
        ("docker availability", check_docker_available),
    ]

    failed = False
    for label, fn in checks:
        ok, output = fn()
        status = "PASS" if ok else "WARN"
        print(f"[{status}] {label}")
        if output:
            print(output)
        if label != "docker availability" and not ok:
            failed = True
        print()

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
