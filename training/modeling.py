from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from datasets import Dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding, Trainer, TrainingArguments

from training.preprocess import normalize_email_text


def compute_classification_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_weighted": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall_weighted": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }


@dataclass(slots=True)
class DatasetBundle:
    train: pd.DataFrame
    valid: pd.DataFrame
    test: pd.DataFrame


def split_dataset(frame: pd.DataFrame, target: str, seed: int = 42) -> DatasetBundle:
    train_valid, test = train_test_split(frame, test_size=0.15, random_state=seed, stratify=frame[target])
    train, valid = train_test_split(train_valid, test_size=0.1765, random_state=seed, stratify=train_valid[target])
    return DatasetBundle(train=train.copy(), valid=valid.copy(), test=test.copy())


def train_classical_classifier(train_frame: pd.DataFrame, eval_frame: pd.DataFrame, target: str, output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=40000)
    model = LogisticRegression(max_iter=250, class_weight="balanced")
    pipeline = Pipeline([("vectorizer", vectorizer), ("model", model)])
    pipeline.fit(train_frame["email_text"], train_frame[target])
    predictions = pipeline.predict(eval_frame["email_text"])
    metrics = compute_classification_metrics(eval_frame[target].tolist(), predictions.tolist())
    joblib.dump(pipeline, output_dir / "model.joblib")
    metadata = {
        "backend": "classical",
        "target": target,
        "labels": sorted(train_frame[target].unique().tolist()),
        "metrics": metrics,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def train_transformer_classifier(
    train_frame: pd.DataFrame,
    valid_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    target: str,
    output_dir: str | Path,
    model_name: str = "distilbert-base-uncased",
    epochs: int = 1,
    batch_size: int = 8,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    labels = sorted(train_frame[target].unique().tolist())
    label_to_id = {label: index for index, label in enumerate(labels)}
    id_to_label = {index: label for label, index in label_to_id.items()}

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def prepare(df: pd.DataFrame) -> Dataset:
        dataset = Dataset.from_pandas(df[["email_text", target]].rename(columns={target: "label_value"}), preserve_index=False)

        def tokenize(batch: dict[str, list[str]]) -> dict[str, Any]:
            encoded = tokenizer(batch["email_text"], truncation=True, padding=False, max_length=256)
            encoded["labels"] = [label_to_id[item] for item in batch["label_value"]]
            return encoded

        return dataset.map(tokenize, batched=True, remove_columns=["email_text", "label_value"])

    train_dataset = prepare(train_frame)
    valid_dataset = prepare(valid_frame)
    test_dataset = prepare(test_frame)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(labels),
        id2label=id_to_label,
        label2id=label_to_id,
    )

    def metric_fn(eval_prediction: tuple[np.ndarray, np.ndarray]) -> dict[str, float]:
        logits, label_ids = eval_prediction
        predictions = np.argmax(logits, axis=-1)
        true_labels = [id_to_label[index] for index in label_ids]
        pred_labels = [id_to_label[index] for index in predictions]
        return compute_classification_metrics(true_labels, pred_labels)

    args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=2e-5,
        num_train_epochs=epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="f1_weighted",
        report_to=[],
        seed=42,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=metric_fn,
    )
    trainer.train()
    prediction_output = trainer.predict(test_dataset)
    predictions = np.argmax(prediction_output.predictions, axis=-1)
    metrics = compute_classification_metrics(
        [id_to_label[index] for index in prediction_output.label_ids],
        [id_to_label[index] for index in predictions],
    )
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    metadata = {
        "backend": "transformer",
        "target": target,
        "labels": labels,
        "label_to_id": label_to_id,
        "metrics": metrics,
        "base_model": model_name,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def load_frame(csv_path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    frame["email_text"] = frame["email_text"].map(normalize_email_text)
    return frame
