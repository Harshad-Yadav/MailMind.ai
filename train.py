from __future__ import annotations

import argparse
import json
from pathlib import Path

from training.data_generator import generate_and_save
from training.modeling import load_frame, split_dataset, train_classical_classifier, train_transformer_classifier

TARGETS = {
    "category": "Email Classification Model",
    "priority": "Priority Prediction Model",
    "department": "Routing Model",
    "spam": "Spam Detection Model",
    "sentiment": "Sentiment Analysis Model",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train enterprise email triage models.")
    parser.add_argument("--dataset-path", default="dataset/emails.csv")
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--backend", choices=["classical", "transformer"], default="classical")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        generate_and_save(rows=args.rows, seed=args.seed)

    frame = load_frame(dataset_path)
    metrics_summary: dict[str, dict[str, object]] = {}
    model_root = Path("models")
    model_root.mkdir(parents=True, exist_ok=True)

    for target, description in TARGETS.items():
        output_dir = model_root / target
        bundle = split_dataset(frame, target=target, seed=args.seed)
        if args.backend == "transformer":
            metadata = train_transformer_classifier(
                train_frame=bundle.train,
                valid_frame=bundle.valid,
                test_frame=bundle.test,
                target=target,
                output_dir=output_dir,
                epochs=args.epochs,
                batch_size=args.batch_size,
            )
        else:
            metadata = train_classical_classifier(
                train_frame=bundle.train,
                eval_frame=bundle.test,
                target=target,
                output_dir=output_dir,
            )
        metrics_summary[target] = {
            "description": description,
            "backend": metadata["backend"],
            "metrics": metadata["metrics"],
        }

    registry = {
        "models": {
            target: {
                "path": f"models/{target}",
                "backend": payload["backend"],
            }
            for target, payload in metrics_summary.items()
        }
    }
    (model_root / "metrics.json").write_text(json.dumps(metrics_summary, indent=2), encoding="utf-8")
    (model_root / "registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(json.dumps(metrics_summary, indent=2))


if __name__ == "__main__":
    main()
