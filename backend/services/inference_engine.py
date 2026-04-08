from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib
from transformers import pipeline

from backend.core.config import get_settings
from training.constants import CATEGORY_TO_DEPARTMENT, DEPARTMENT_TO_RESPONSE_TONE

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class InferenceEngine:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.registry = self._load_registry()
        self.semantic_encoder: Any | None = None
        self.enable_semantic_encoder = os.getenv("ENABLE_SENTENCE_ENCODER", "0") == "1"
        self._cache: dict[str, Any] = {}

    def _load_registry(self) -> dict[str, Any]:
        registry_path = Path(self.settings.model_registry_path)
        if not registry_path.exists():
            return {}
        return json.loads(registry_path.read_text(encoding="utf-8"))

    def _get_semantic_encoder(self) -> Any | None:
        if not self.enable_semantic_encoder:
            return None
        if self.semantic_encoder is not None:
            return self.semantic_encoder
        if SentenceTransformer is None:
            return None
        try:
            self.semantic_encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True)
        except Exception:
            self.semantic_encoder = None
        return self.semantic_encoder

    def _load_model(self, target: str) -> tuple[str, Any]:
        if target in self._cache:
            return self._cache[target]
        model_info = self.registry.get("models", {}).get(target)
        if not model_info:
            self._cache[target] = ("heuristic", None)
            return self._cache[target]
        model_path = Path(model_info["path"])
        backend = model_info["backend"]
        if backend == "classical":
            loaded = joblib.load(model_path / "model.joblib")
        elif backend == "transformer":
            loaded = pipeline("text-classification", model=str(model_path), tokenizer=str(model_path), truncation=True)
        else:
            loaded = None
        self._cache[target] = (backend, loaded)
        return self._cache[target]

    def _predict_single(self, target: str, text: str) -> Any:
        backend, model = self._load_model(target)
        if backend == "classical" and model is not None:
            return model.predict([text])[0]
        if backend == "transformer" and model is not None:
            result = model(text, top_k=1)[0]
            return result["label"]
        return None

    def _heuristic_predict(self, text: str) -> dict[str, Any]:
        lowered = text.lower()
        category = "operations"
        if any(word in lowered for word in ["invoice", "payment", "billing", "charge"]):
            category = "billing"
        elif any(word in lowered for word in ["login", "error", "bug", "sync", "dashboard"]):
            category = "technical_support"
        elif any(word in lowered for word in ["pricing", "demo", "procurement", "quote"]):
            category = "sales"
        elif any(word in lowered for word in ["contract", "dpa", "msa", "indemnification", "legal"]):
            category = "legal"
        elif any(word in lowered for word in ["harassment", "benefits", "policy", "employee", "manager", "parental", "leave", "handbook", "termination"]):
            category = "human_resources"
        elif any(word in lowered for word in ["security", "suspicious", "breach", "soc2", "vulnerability", "auth", "access"]):
            category = "security"
        elif any(word in lowered for word in ["warehouse", "shipment", "batch", "operations", "kpi"]):
            category = "operations"
        elif any(word in lowered for word in ["partner", "reseller", "integration", "co-marketing"]):
            category = "partnership"

        spam = int(any(word in lowered for word in ["guaranteed", "bonus transfer", "crypto", "zero risk"]))
        urgency = "low"
        if any(word in lowered for word in ["one business day", "tomorrow"]):
            urgency = "medium"
        if any(word in lowered for word in ["end of day", "today", "customer impact"]):
            urgency = "high"
        if any(word in lowered for word in ["immediate action", "within the hour", "severe impact"]):
            urgency = "critical"

        sentiment = "neutral"
        if any(word in lowered for word in ["appreciate", "good experience", "thanks"]):
            sentiment = "positive"
        if any(word in lowered for word in ["disrupting", "disappointed", "below expectations"]):
            sentiment = "negative"
        if any(word in lowered for word in ["unacceptable", "escalating", "costing us money"]):
            sentiment = "frustrated"

        priority = "low"
        if urgency == "medium":
            priority = "medium"
        elif urgency == "high":
            priority = "high"
        elif urgency == "critical":
            priority = "critical"
        if category in {"security", "legal"} and priority in {"medium", "high"}:
            priority = "high"
        if category == "security" and urgency == "critical":
            priority = "critical"

        department = CATEGORY_TO_DEPARTMENT[category]
        return {
            "category": category,
            "priority": priority,
            "department": department,
            "spam": spam,
            "sentiment": sentiment,
            "urgency": urgency,
        }

    def predict(self, text: str, customer_name: str = "Customer") -> dict[str, Any]:
        result = self._heuristic_predict(text)
        for target in ["category", "priority", "department", "spam", "sentiment"]:
            predicted = self._predict_single(target, text)
            if predicted is None:
                continue
            if target == "spam":
                result[target] = int(str(predicted).lower() in {"1", "spam", "true"})
            else:
                result[target] = str(predicted).lower()

        department = result["department"]
        tone = DEPARTMENT_TO_RESPONSE_TONE.get(department, "professional")
        semantic_hint = 0.0
        encoder = self._get_semantic_encoder()
        if encoder is not None:
            try:
                semantic_hint = float(encoder.encode([text])[0].mean())
            except Exception:
                semantic_hint = 0.0
        response_draft = (
            f"Hello {customer_name},\n\n"
            f"We reviewed your email and routed it to our {department} team. "
            f"This looks like a {result['priority']} priority {result['category'].replace('_', ' ')} issue. "
            f"Our reply will be {tone}, and we have flagged urgency as {result['urgency']}. "
            f"Reference signal score: {semantic_hint:.3f}.\n\n"
            "Best,\nEnterprise Triage"
        )
        result["response_draft"] = response_draft
        result["escalation"] = result["priority"] == "critical" or result["category"] == "security"
        return result
