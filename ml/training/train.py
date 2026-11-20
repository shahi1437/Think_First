"""Reproducible training and group-aware held-out evaluation for CodeMentor AI error classifier.

Prevents train/test leakage by splitting strictly on `program_family` using
StratifiedGroupKFold so mutations of the same reference program never appear
in both train and test partitions.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline

from ml.preprocessing.features import ERROR_TAXONOMY, ExecutionSample, build_feature_document
from ml.training.baselines import RuleBasedErrorClassifier

MODEL_VERSION = "error-clf-v1.0.0"
DATASET_VERSION = "python_errors_v1"
LOW_CONFIDENCE_THRESHOLD = 0.55


def _row_to_sample(row: dict[str, Any]) -> ExecutionSample:
    return ExecutionSample(
        source_code=str(row["source_code"]),
        verdict=str(row["verdict"]),
        stderr="" if pd.isna(row["stderr"]) else str(row["stderr"]),
        compile_output="" if pd.isna(row["compile_output"]) else str(row["compile_output"]),
        stdout_actual="" if pd.isna(row["stdout_actual"]) else str(row["stdout_actual"]),
        stdout_expected="" if pd.isna(row["stdout_expected"]) else str(row["stdout_expected"]),
        passed_tests=int(row["passed_tests"]),
        total_tests=int(row["total_tests"]),
    )


def _build_vectorizer() -> FeatureUnion:
    return FeatureUnion(
        [
            (
                "word_ngrams",
                TfidfVectorizer(
                    analyzer="word",
                    token_pattern=r"[A-Za-z_][A-Za-z0-9_]*|[!=<>]=|[+\-*/%]=?|[:()\[\]]",
                    ngram_range=(1, 2),
                    min_df=2,
                    sublinear_tf=True,
                ),
            ),
            (
                "char_ngrams",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=3,
                    max_features=4000,
                    sublinear_tf=True,
                ),
            ),
        ]
    )


def _compute_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    labels = list(ERROR_TAXONOMY)
    report_dict = classification_report(
        y_true, y_pred, labels=labels, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    per_class = {
        lbl: {
            "precision": round(float(report_dict[lbl]["precision"]), 4),
            "recall": round(float(report_dict[lbl]["recall"]), 4),
            "f1": round(float(report_dict[lbl]["f1-score"]), 4),
            "support": int(report_dict[lbl]["support"]),
        }
        for lbl in labels
    }
    return {
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "weighted_f1": round(
            float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4
        ),
        "macro_precision": round(
            float(precision_score(y_true, y_pred, average="macro", zero_division=0)), 4
        ),
        "macro_recall": round(
            float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4
        ),
        "per_class": per_class,
        "labels": labels,
        "confusion_matrix": cm,
    }


def train_and_evaluate(repo_root: Path) -> dict[str, Any]:
    csv_path = repo_root / "ml" / "datasets" / f"{DATASET_VERSION}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {csv_path}. Run ml/preprocessing/generate_dataset.py first."
        )

    df = pd.read_csv(csv_path)
    records = df.to_dict(orient="records")
    samples = [_row_to_sample(r) for r in records]
    docs = [build_feature_document(s) for s in samples]
    labels = [str(r["label"]) for r in records]
    groups = [str(r["program_family"]) for r in records]

    # Strict 5-fold StratifiedGroupKFold: fold 0 is held-out test (~20% of program families)
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    splits = list(sgkf.split(docs, labels, groups))
    train_idx, test_idx = splits[0]

    train_families = {groups[i] for i in train_idx}
    test_families = {groups[i] for i in test_idx}
    assert train_families.isdisjoint(test_families), "Program family leakage detected!"

    x_train = [docs[i] for i in train_idx]
    y_train = [labels[i] for i in train_idx]
    x_test = [docs[i] for i in test_idx]
    y_test = [labels[i] for i in test_idx]
    test_samples = [samples[i] for i in test_idx]

    # 1. Rule-Based Baseline
    rule_clf = RuleBasedErrorClassifier()
    rule_preds = rule_clf.predict(test_samples)
    rule_metrics = _compute_metrics(y_test, rule_preds)

    # 2. Primary Candidate: TF-IDF + Logistic Regression
    logreg_pipe = Pipeline(
        [
            ("features", _build_vectorizer()),
            (
                "clf",
                LogisticRegression(
                    C=2.5,
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    logreg_pipe.fit(x_train, y_train)
    logreg_preds = list(logreg_pipe.predict(x_test))
    logreg_metrics = _compute_metrics(y_test, logreg_preds)

    # 5-fold StratifiedGroupKFold CV Macro F1 for Logistic Regression
    cv_scores: list[float] = []
    for tr_i, va_i in splits:
        fold_pipe = Pipeline(
            [
                ("features", _build_vectorizer()),
                (
                    "clf",
                    LogisticRegression(
                        C=2.5, max_iter=1000, class_weight="balanced", random_state=42
                    ),
                ),
            ]
        )
        fold_pipe.fit([docs[i] for i in tr_i], [labels[i] for i in tr_i])
        fold_preds = list(fold_pipe.predict([docs[i] for i in va_i]))
        cv_scores.append(
            float(f1_score([labels[i] for i in va_i], fold_preds, average="macro", zero_division=0))
        )

    # 3. Secondary Candidate: TF-IDF + Random Forest
    rf_pipe = Pipeline(
        [
            ("features", _build_vectorizer()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=250,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    rf_pipe.fit(x_train, y_train)
    rf_preds = list(rf_pipe.predict(x_test))
    rf_metrics = _compute_metrics(y_test, rf_preds)

    # Fit final production artifact on full validated dataset after held-out evaluation
    final_pipe = Pipeline(
        [
            ("features", _build_vectorizer()),
            (
                "clf",
                LogisticRegression(
                    C=2.5,
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    final_pipe.fit(docs, labels)

    trained_at = datetime.now(UTC).isoformat()
    artifact_dir = repo_root / "ml" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "error_classifier_v1.joblib"

    artifact_bundle = {
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "trained_at": trained_at,
        "taxonomy": list(ERROR_TAXONOMY),
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "pipeline": final_pipe,
        "holdout_macro_f1": logreg_metrics["macro_f1"],
        "cv_macro_f1_mean": round(float(np.mean(cv_scores)), 4),
    }
    joblib.dump(artifact_bundle, artifact_path)

    eval_report = {
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "trained_at": trained_at,
        "split_strategy": "StratifiedGroupKFold(n_splits=5, grouped by program_family)",
        "total_samples": len(df),
        "total_program_families": len(set(groups)),
        "train_samples": len(train_idx),
        "test_samples": len(test_idx),
        "train_families": len(train_families),
        "test_families": len(test_families),
        "family_leakage_count": len(train_families.intersection(test_families)),
        "cv_5fold_logreg_macro_f1": {
            "folds": [round(s, 4) for s in cv_scores],
            "mean": round(float(np.mean(cv_scores)), 4),
            "std": round(float(np.std(cv_scores)), 4),
        },
        "models": {
            "rule_based_baseline": rule_metrics,
            "tfidf_logistic_regression": logreg_metrics,
            "tfidf_random_forest": rf_metrics,
        },
        "selected_model": "tfidf_logistic_regression",
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
    }

    eval_dir = repo_root / "ml" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "eval_report_v1.json").write_text(
        json.dumps(eval_report, indent=2), encoding="utf-8"
    )
    _write_markdown_report(repo_root / "docs" / "ai" / "ml-evaluation-report.md", eval_report)
    return eval_report


def _write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lr = report["models"]["tfidf_logistic_regression"]
    rb = report["models"]["rule_based_baseline"]
    rf = report["models"]["tfidf_random_forest"]
    cv = report["cv_5fold_logreg_macro_f1"]

    lines = [
        "# ML Error Classifier Evaluation Report (`error-clf-v1.0.0`)",
        "",
        f"- **Dataset Version:** `{report['dataset_version']}`",
        f"- **Trained At (UTC):** `{report['trained_at']}`",
        f"- **Total Execution-Validated Samples:** `{report['total_samples']}` across `{report['total_program_families']}` original Python program families",
        f"- **Split Strategy:** `{report['split_strategy']}` (Train: `{report['train_samples']}` samples / `{report['train_families']}` families; Held-Out Test: `{report['test_samples']}` samples / `{report['test_families']}` families; Family Leakage: `{report['family_leakage_count']}`)",
        f"- **Selected Model:** `TF-IDF (word + char n-grams + AST/execution cues) + Logistic Regression` (Low-confidence threshold: `{report['low_confidence_threshold']}`)",
        "",
        "## Model Comparison (Held-Out Unseen Program Families)",
        "",
        "| Model | Macro F1 | Weighted F1 | Macro Precision | Macro Recall |",
        "| :--- | :---: | :---: | :---: | :---: |",
        f"| Rule-Based Baseline | {rb['macro_f1']} | {rb['weighted_f1']} | {rb['macro_precision']} | {rb['macro_recall']} |",
        f"| **TF-IDF + Logistic Regression (Selected)** | **{lr['macro_f1']}** | **{lr['weighted_f1']}** | **{lr['macro_precision']}** | **{lr['macro_recall']}** |",
        f"| TF-IDF + Random Forest | {rf['macro_f1']} | {rf['weighted_f1']} | {rf['macro_precision']} | {rf['macro_recall']} |",
        "",
        f"- **5-Fold Grouped CV Macro F1 (Logistic Regression):** Mean `{cv['mean']}` ± `{cv['std']}` (Folds: `{cv['folds']}`)",
        "",
        "## Per-Class Performance (TF-IDF + Logistic Regression, Held-Out Test)",
        "",
        "| Error Class | Precision | Recall | F1 | Support |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for lbl in lr["labels"]:
        m = lr["per_class"][lbl]
        lines.append(
            f"| `{lbl}` | {m['precision']} | {m['recall']} | {m['f1']} | {m['support']} |"
        )

    lines.extend(
        [
            "",
            "## Confusion Matrix (Rows = True, Cols = Predicted)",
            "",
            "| True \\ Pred | " + " | ".join(lr["labels"]) + " |",
            "| :--- | " + " | ".join([":---:"] * len(lr["labels"])) + " |",
        ]
    )
    for lbl, row in zip(lr["labels"], lr["confusion_matrix"], strict=True):
        lines.append(f"| `{lbl}` | " + " | ".join(str(v) for v in row) + " |")

    lines.extend(
        [
            "",
            "## Reproduction Commands",
            "",
            "```bash",
            "# From Think_First repository root using backend virtualenv",
            "backend/.venv/Scripts/python.exe -m ml.preprocessing.generate_dataset",
            "backend/.venv/Scripts/python.exe -m ml.training.train",
            "```",
            "",
            "## Documented Limitations",
            "",
            "- Dataset covers 40 original beginner-to-basic Python problem families with controlled single-fault mutations; multi-fault student submissions or unseen algorithmic paradigms may yield lower confidence and are explicitly flagged (`is_low_confidence = true`) rather than presented as certain.",
            "- Directly observable syntax and runtime exceptions are easier to separate than overlapping semantic mistakes (`condition_error` vs `logic_error`).",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    report = train_and_evaluate(root)
    print(json.dumps(report, indent=2))
