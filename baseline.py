from __future__ import annotations

import argparse
import json

from backend.services.baseline_service import OpenAIBaselineService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the OpenAI baseline across all email triage tasks.")
    parser.add_argument("--model", default=None)
    parser.add_argument("--episodes-per-task", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = OpenAIBaselineService()
    result = service.run(model=args.model, episodes_per_task=args.episodes_per_task, seed=args.seed)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
