from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.core.config import get_settings
from training.data_generator import generate_and_save
from training.preprocess import normalize_email_text


class DatasetService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._frame: pd.DataFrame | None = None
        self._model_metrics: dict[str, object] | None = None

    def load(self) -> pd.DataFrame:
        if self._frame is not None:
            return self._frame
        dataset_path = Path(self.settings.dataset_path)
        if not dataset_path.exists():
            generate_and_save(rows=self.settings.sample_size, seed=self.settings.default_seed)
        
        try:
            frame = pd.read_csv(dataset_path)
        except Exception as e:
            print(f"WARN: Failed to read dataset CSV: {e}")
            frame = pd.DataFrame()

        if "email_id" not in frame.columns and not frame.empty:
            import uuid
            frame.insert(0, "email_id", [str(uuid.uuid4()) for _ in range(len(frame))])

        initial_len = len(frame)
        if not frame.empty:
            frame = frame.dropna(subset=["subject", "email_text", "category", "priority"])
            
        if len(frame) < initial_len:
            print(f"WARN: Dropped {initial_len - len(frame)} malformed records from dataset.")

        if not frame.empty:
            frame["email_text"] = frame["email_text"].astype(str).map(normalize_email_text)
            
        self._frame = frame
        return self._frame

    def sample(self, seed: int, spam_only: bool = False) -> dict[str, object]:
        frame = self.load()
        candidate = frame[frame["spam"] == 1] if spam_only else frame
        row = candidate.sample(n=1, random_state=seed).iloc[0]
        return row.to_dict()

    def load_model_metrics(self) -> dict[str, object]:
        if self._model_metrics is not None:
            return self._model_metrics
        metrics_path = Path(self.settings.metrics_path)
        if metrics_path.exists():
            self._model_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        else:
            self._model_metrics = {}
        return self._model_metrics

    def analytics_snapshot(self) -> dict[str, object]:
        frame = self.load()
        sla_risk = frame["priority"].map({"low": "healthy", "medium": "healthy", "high": "at_risk", "critical": "breached"})
        model_metrics = self.load_model_metrics()
        return {
            "total_emails": int(len(frame)),
            "category_distribution": frame["category"].value_counts().to_dict(),
            "priority_distribution": frame["priority"].value_counts().to_dict(),
            "sentiment_distribution": frame["sentiment"].value_counts().to_dict(),
            "urgency_distribution": frame["urgency"].value_counts().to_dict(),
            "spam_rate": float(frame["spam"].mean()),
            "strategic_customer_rate": float((frame["customer_tier"] == "strategic").mean()),
            "sla_risk_distribution": sla_risk.value_counts().to_dict(),
            "model_metrics": model_metrics,
        }
