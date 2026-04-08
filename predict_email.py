from __future__ import annotations

import argparse
import json

from backend.services.inference_engine import InferenceEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local model-assisted email triage inference.")
    parser.add_argument("--email-text", required=True)
    parser.add_argument("--customer-name", default="Customer")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = InferenceEngine()
    result = engine.predict(args.email_text, customer_name=args.customer_name)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
