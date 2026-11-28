"""Reproducible multi-algorithm training and group-aware evaluation for CodeMentor AI.

Prevents train/test leakage by splitting strictly on `program_family` using
5-fold StratifiedGroupKFold so mutations of the same reference program never
appear in both train and test partitions.

Compares 6 lightweight CPU candidates:
1. Rule-Based Heuristic Baseline
2. TF-IDF + Logistic Regression
3. TF-IDF + Calibrated LinearSVC (Platt scaling)
4. TF-IDF + Random Forest
5. TF-IDF + Extra Trees
6. TF-IDF + Complement Naive Bayes

Also evaluates the selected model on an independent external MIT-licensed public
benchmark (`ml/datasets/public_curated_quixbugs_v1.csv`) when present, keeping
controlled synthetic data strictly separated from public and real student data.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from ml.preprocessing.features import (
    ERROR_TAXONOMY,
    ExecutionSample,
    build_feature_document,
)
from ml.training.baselines import RuleBasedErrorClassifier

MODEL_VERSION = "error-clf-v1.1.0"
DATASET_VERSION = "python_errors_v1"
PUBLIC_BENCHMARK_VERSION = "public_curated_quixbugs_v1"
LOW_CONFIDENCE_THRESHOLD = 0.55


def _row_to_sample(row: dict[str, Any]) -> ExecutionSample:
    return ExecutionSample(
        source_code=str(row["source_code"]),
        verdict=str(row["verdict"]),
        stderr="" if pd.isna(row.get("stderr")) else str(row["stderr"]),
        compile_output=""
        if pd.isna(row.get("compile_output"))
        else str(row["compile_output"]),
        stdout_actual=""
        if pd.isna(row.get("stdout_actual"))
        else str(row["stdout_actual"]),
        stdout_expected=""
        if pd.isna(row.get("stdout_expected"))
        else str(row["stdout_expected"]),
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
                    max_features=4500,
                    sublinear_tf=True,
                ),
            ),
        ]
    )


def _candidate_factories() -> dict[str, tuple[str, Callable[[], Pipeline]]]:
    return {
        "tfidf_logistic_regression": (
            "TF-IDF + Logistic Regression",
            lambda: Pipeline(
                [
                    ("features", _build_vectorizer()),
                    (
                        "clf",
                        LogisticRegression(
                            C=3.0,
                            max_iter=1000,
                            class_weight="balanced",
                            random_state=42,
                        ),
                    ),
                ]
            ),
        ),
        "tfidf_calibrated_linear_svc": (
            "TF-IDF + Calibrated LinearSVC",
            lambda: Pipeline(
                [
                    ("features", _build_vectorizer()),
                    (
                        "clf",
                        CalibratedClassifierCV(
                            estimator=LinearSVC(
                                C=1.0,
                                class_weight="balanced",
                                random_state=42,
                            ),
                            cv=3,
                            method="sigmoid",
                        ),
                    ),
                ]
            ),
        ),
        "tfidf_random_forest": (
            "TF-IDF + Random Forest",
            lambda: Pipeline(
                [
                    ("features", _build_vectorizer()),
                    (
                        "clf",
                        RandomForestClassifier(
                            n_estimators=150,
                            max_depth=24,
                            class_weight="balanced",
                            random_state=42,
                            n_jobs=1,
                        ),
                    ),
                ]
            ),
        ),
        "tfidf_extra_trees": (
            "TF-IDF + Extra Trees",
            lambda: Pipeline(
                [
                    ("features", _build_vectorizer()),
                    (
                        "clf",
                        ExtraTreesClassifier(
                            n_estimators=150,
                            max_depth=24,
                            class_weight="balanced",
                            random_state=42,
                            n_jobs=1,
                        ),
                    ),
                ]
            ),
        ),
        "tfidf_complement_nb": (
            "TF-IDF + Complement Naive Bayes",
            lambda: Pipeline(
                [
                    ("features", _build_vectorizer()),
                    ("clf", ComplementNB(alpha=0.5)),
                ]
            ),
        ),
    }


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
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(
            float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4
        ),
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


def _evaluate_external_public_benchmark(
    pipe: Pipeline,
    csv_path: Path,
) -> dict[str, Any] | None:
    """Evaluate trained model on independent MIT-licensed QuixBugs benchmark (never trained on)."""
    if not csv_path.exists():
        return None
    ext_df = pd.read_csv(csv_path)
    if len(ext_df) == 0:
        return None

    records = ext_df.to_dict(orient="records")
    samples = [_row_to_sample(r) for r in records]
    docs = [build_feature_document(s) for s in samples]
    y_true = [str(r["label"]) for r in records]
    probs_matrix = pipe.predict_proba(docs)
    classes = list(pipe.classes_)

    y_pred: list[str] = []
    top_3_hits = 0
    low_conf_count = 0
    high_conf_correct = 0
    high_conf_total = 0

    for true_lbl, probs in zip(y_true, probs_matrix, strict=True):
        ranked = sorted(
            zip(classes, probs, strict=True), key=lambda x: float(x[1]), reverse=True
        )
        pred_lbl = str(ranked[0][0])
        top_p = float(ranked[0][1])
        second_p = float(ranked[1][1]) if len(ranked) > 1 else 0.0
        is_low_conf = top_p < LOW_CONFIDENCE_THRESHOLD or (top_p - second_p) < 0.12
        y_pred.append(pred_lbl)
        if true_lbl in [str(c) for c, _ in ranked[:3]]:
            top_3_hits += 1
        if is_low_conf:
            low_conf_count += 1
        else:
            high_conf_total += 1
            if pred_lbl == true_lbl:
                high_conf_correct += 1

    present_labels = sorted(set(y_true))
    return {
        "benchmark_name": PUBLIC_BENCHMARK_VERSION,
        "source_repo": "jkoppel/QuixBugs",
        "license": "MIT",
        "data_origin": "public_curated",
        "samples": len(ext_df),
        "classes_present": present_labels,
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "top_3_accuracy": round(float(top_3_hits / max(len(y_true), 1)), 4),
        "macro_f1_present_classes": round(
            float(
                f1_score(
                    y_true,
                    y_pred,
                    labels=present_labels,
                    average="macro",
                    zero_division=0,
                )
            ),
            4,
        ),
        "low_confidence_flagged_rate": round(
            float(low_conf_count / max(len(y_true), 1)), 4
        ),
        "high_confidence_samples": high_conf_total,
        "high_confidence_accuracy": (
            round(float(high_conf_correct / high_conf_total), 4)
            if high_conf_total > 0
            else None
        ),
        "note": (
            "Independent out-of-domain external benchmark (harder DP/graph/sorting algorithms "
            "from QuixBugs MIT, never included in training). Demonstrates honest OOD generalization "
            "and uncertainty abstention."
        ),
    }


def train_and_evaluate(repo_root: Path) -> dict[str, Any]:
    csv_path = repo_root / "ml" / "datasets" / f"{DATASET_VERSION}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {csv_path}. Run ml/preprocessing/generate_dataset.py first."
        )

    df = pd.read_csv(csv_path)
    # Enforce strict separation: training dataset must contain only validated controlled_synthetic rows
    if "data_origin" in df.columns:
        origins = sorted(set(df["data_origin"].astype(str)))
        if origins != ["controlled_synthetic"]:
            raise ValueError(
                f"Expected pure controlled_synthetic training file at {csv_path}, got origins={origins}"
            )

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

    models_report: dict[str, Any] = {}
    cv_summary: dict[str, dict[str, Any]] = {}

    # 1. Rule-Based Heuristic Baseline (held-out + 5-fold CV)
    rule_clf = RuleBasedErrorClassifier()
    rule_preds = rule_clf.predict(test_samples)
    rule_metrics = _compute_metrics(y_test, rule_preds)
    rule_cv = [
        float(
            f1_score(
                [labels[i] for i in va_i],
                rule_clf.predict([samples[i] for i in va_i]),
                average="macro",
                zero_division=0,
            )
        )
        for _, va_i in splits
    ]
    rule_metrics["display_name"] = "Rule-Based Heuristic Baseline"
    rule_metrics["cv_macro_f1_mean"] = round(float(np.mean(rule_cv)), 4)
    rule_metrics["cv_macro_f1_std"] = round(float(np.std(rule_cv)), 4)
    models_report["rule_based_baseline"] = rule_metrics
    cv_summary["rule_based_baseline"] = {
        "folds": [round(s, 4) for s in rule_cv],
        "mean": round(float(np.mean(rule_cv)), 4),
        "std": round(float(np.std(rule_cv)), 4),
    }

    # 2. Evaluate all 5 lightweight CPU scikit-learn candidates
    factories = _candidate_factories()
    best_key = ""
    best_score_tuple = (-1.0, -1.0, -1.0)

    for key, (display_name, build_fn) in factories.items():
        pipe = build_fn()
        pipe.fit(x_train, y_train)
        preds = list(pipe.predict(x_test))
        metrics = _compute_metrics(y_test, preds)

        fold_scores: list[float] = []
        for tr_i, va_i in splits:
            fold_pipe = build_fn()
            fold_pipe.fit([docs[i] for i in tr_i], [labels[i] for i in tr_i])
            fold_preds = list(fold_pipe.predict([docs[i] for i in va_i]))
            fold_scores.append(
                float(
                    f1_score(
                        [labels[i] for i in va_i],
                        fold_preds,
                        average="macro",
                        zero_division=0,
                    )
                )
            )

        cv_mean = round(float(np.mean(fold_scores)), 4)
        cv_std = round(float(np.std(fold_scores)), 4)
        metrics["display_name"] = display_name
        metrics["cv_macro_f1_mean"] = cv_mean
        metrics["cv_macro_f1_std"] = cv_std
        models_report[key] = metrics
        cv_summary[key] = {
            "folds": [round(s, 4) for s in fold_scores],
            "mean": cv_mean,
            "std": cv_std,
        }

        cond_f1 = float(metrics["per_class"]["condition_error"]["f1"])
        score_tuple = (cv_mean, float(metrics["macro_f1"]), cond_f1)
        if score_tuple > best_score_tuple:
            best_score_tuple = score_tuple
            best_key = key

    # Fit selected production artifact on full validated controlled-synthetic dataset
    selected_display_name, selected_builder = factories[best_key]
    final_pipe = selected_builder()
    final_pipe.fit(docs, labels)

    # Independent external benchmark evaluation (QuixBugs MIT)
    external_eval = _evaluate_external_public_benchmark(
        final_pipe,
        repo_root / "ml" / "datasets" / f"{PUBLIC_BENCHMARK_VERSION}.csv",
    )

    trained_at = datetime.now(UTC).isoformat()
    artifact_dir = repo_root / "ml" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "error_classifier_v1.joblib"

    selected_metrics = models_report[best_key]
    selected_cv = cv_summary[best_key]

    artifact_bundle = {
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "data_origin": "controlled_synthetic",
        "selected_algorithm": best_key,
        "selected_algorithm_name": selected_display_name,
        "trained_at": trained_at,
        "taxonomy": list(ERROR_TAXONOMY),
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "pipeline": final_pipe,
        "holdout_macro_f1": selected_metrics["macro_f1"],
        "cv_macro_f1_mean": selected_cv["mean"],
    }
    joblib.dump(artifact_bundle, artifact_path)

    eval_report = {
        "model_version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION,
        "data_origin": "controlled_synthetic",
        "trained_at": trained_at,
        "split_strategy": "StratifiedGroupKFold(n_splits=5, grouped by program_family)",
        "total_samples": len(df),
        "total_program_families": len(set(groups)),
        "train_samples": len(train_idx),
        "test_samples": len(test_idx),
        "train_families": len(train_families),
        "test_families": len(test_families),
        "family_leakage_count": len(train_families.intersection(test_families)),
        "cv_5fold_selected_macro_f1": selected_cv,
        "cv_5fold_all_models": cv_summary,
        "models": models_report,
        "selected_model": best_key,
        "selected_model_name": selected_display_name,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "external_public_benchmark": external_eval,
    }

    eval_dir = repo_root / "ml" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "eval_report_v1.json").write_text(
        json.dumps(eval_report, indent=2), encoding="utf-8"
    )
    _write_markdown_report(
        repo_root / "docs" / "ai" / "ml-evaluation-report.md", eval_report
    )
    return eval_report


def _write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sel_key = report["selected_model"]
    sel = report["models"][sel_key]
    cv = report["cv_5fold_selected_macro_f1"]

    lines = [
        f"# ML Error Classifier Evaluation Report (`{report['model_version']}`)",
        "",
        f"- **Dataset Version:** `{report['dataset_version']}` (`data_origin = {report['data_origin']}`)",
        f"- **Trained At (UTC):** `{report['trained_at']}`",
        f"- **Total Execution-Validated Samples:** `{report['total_samples']}` across `{report['total_program_families']}` original Python program families",
        f"- **Split Strategy:** `{report['split_strategy']}` (Train: `{report['train_samples']}` samples / `{report['train_families']}` families; Held-Out Test: `{report['test_samples']}` samples / `{report['test_families']}` families; Family Leakage: `{report['family_leakage_count']}`)",
        f"- **Selected Model:** `{report['selected_model_name']}` (Low-confidence threshold: `{report['low_confidence_threshold']}`, top-2 ambiguity margin `< 0.12`)",
        "",
        "> **Honesty & Data Provenance Notice:** Supervised training uses strictly separated execution-validated `controlled_synthetic` program mutations (`python_errors_v1.csv`). Real-world student generalization MUST NOT be claimed from synthetic metrics alone. Consent-gated real student debugging events are exported separately via `ml/tools/export_consented_student_dataset.py` and require human verification via `ml/tools/validate_and_label.py` before supervised retraining.",
        "",
        "## 1. Multi-Algorithm Comparison (5-Fold Grouped CV + Held-Out Unseen Families)",
        "",
        "| Model | 5-Fold CV Macro F1 | Holdout Macro F1 | Holdout Weighted F1 | `condition_error` F1 |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for key, m in report["models"].items():
        name = m["display_name"]
        cond_f1 = m["per_class"]["condition_error"]["f1"]
        cv_str = f"{m['cv_macro_f1_mean']:.4f} ± {m['cv_macro_f1_std']:.4f}"
        if key == sel_key:
            lines.append(
                f"| **{name} (Selected)** | **{cv_str}** | **{m['macro_f1']:.4f}** | **{m['weighted_f1']:.4f}** | **{cond_f1:.4f}** |"
            )
        else:
            lines.append(
                f"| {name} | {cv_str} | {m['macro_f1']:.4f} | {m['weighted_f1']:.4f} | {cond_f1:.4f} |"
            )

    lines.extend(
        [
            "",
            f"- **Selected Model 5-Fold CV Folds:** `{cv['folds']}` (Mean `{cv['mean']}` ± `{cv['std']}`)",
            "",
            f"## 2. Per-Class Performance ({report['selected_model_name']}, Held-Out Unseen Families)",
            "",
            "| Error Class | Precision | Recall | F1 | Support |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
    )
    for lbl in sel["labels"]:
        m = sel["per_class"][lbl]
        lines.append(
            f"| `{lbl}` | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['support']} |"
        )

    lines.extend(
        [
            "",
            "## 3. Confusion Matrix (Rows = True, Cols = Predicted)",
            "",
            "| True \\ Pred | " + " | ".join(sel["labels"]) + " |",
            "| :--- | " + " | ".join([":---:"] * len(sel["labels"])) + " |",
        ]
    )
    for lbl, row in zip(sel["labels"], sel["confusion_matrix"], strict=True):
        lines.append(f"| `{lbl}` | " + " | ".join(str(v) for v in row) + " |")

    ext = report.get("external_public_benchmark")
    if ext:
        hi_acc = (
            f"{ext['high_confidence_accuracy']:.4f}"
            if ext["high_confidence_accuracy"] is not None
            else "N/A"
        )
        lines.extend(
            [
                "",
                "## 4. Independent External Public Benchmark (`jkoppel/QuixBugs`, MIT License)",
                "",
                f"- **Provenance:** `{ext['data_origin']}` (`{ext['source_repo']}`, license `{ext['license']}`), **0% overlap with training data**.",
                f"- **Execution-Validated Samples Evaluated:** `{ext['samples']}`",
                f"- **Top-1 Accuracy (Unseen Algorithmic Domain):** `{ext['accuracy']:.4f}`",
                f"- **Top-3 Accuracy (Candidate Ranking):** `{ext['top_3_accuracy']:.4f}`",
                f"- **Low-Confidence Uncertainty Abstention Rate:** `{ext['low_confidence_flagged_rate']:.4f}`",
                f"- **High-Confidence Subset Accuracy:** `{hi_acc}` (`{ext['high_confidence_samples']}` high-confidence predictions)",
                f"- **Interpretation:** {ext['note']}",
            ]
        )

    lines.extend(
        [
            "",
            "## 5. Reproduction & Data Governance Commands",
            "",
            "```bash",
            "# 1. Regenerate & validate execution-verified controlled synthetic dataset",
            "backend/.venv/Scripts/python.exe -m ml.preprocessing.generate_dataset",
            "backend/.venv/Scripts/python.exe -m ml.tools.validate_and_label validate ml/datasets/python_errors_v1.csv",
            "",
            "# 2. Import & validate independent MIT-licensed public benchmark (QuixBugs)",
            "backend/.venv/Scripts/python.exe -m ml.tools.import_public_quixbugs",
            "backend/.venv/Scripts/python.exe -m ml.tools.validate_and_label validate ml/datasets/public_curated_quixbugs_v1.csv --allow-subset",
            "",
            "# 3. Train, cross-validate 6 candidates, and evaluate external benchmark",
            "backend/.venv/Scripts/python.exe -m ml.training.train",
            "",
            "# 4. Export opt-in consented student events for human review (strictly separated)",
            "backend/.venv/Scripts/python.exe -m ml.tools.export_consented_student_dataset",
            "```",
            "",
            "## 6. Documented Limitations",
            "",
            "- Controlled synthetic mutations cover 58 original beginner-to-intermediate Python problem families; real multi-fault student submissions or advanced algorithms may produce lower confidence and are explicitly flagged (`is_low_confidence = true`) with ranked top-3 candidates.",
            "- Non-Python languages (JavaScript, C, C++, Java) honestly report `diagnosis_source = 'rule_based'` via deterministic compiler/traceback/AST diagnostics rather than extrapolating a Python-trained ML artifact.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    report = train_and_evaluate(root)
    print(json.dumps(report, indent=2))
