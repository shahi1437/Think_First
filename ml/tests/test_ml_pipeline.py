import json
from pathlib import Path

import joblib
import pandas as pd

from ml.preprocessing.features import (
    ERROR_TAXONOMY,
    ExecutionSample,
    build_feature_document,
)
from ml.tools.export_consented_student_dataset import (
    pseudonymize_student_id,
    sanitize_source_code,
)
from ml.tools.validate_and_label import relabel_sample, validate_dataset


def test_dataset_and_model_artifact_exist_and_predict_valid_classes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    csv_path = repo_root / "ml" / "datasets" / "python_errors_v1.csv"
    artifact_path = repo_root / "ml" / "artifacts" / "error_classifier_v1.joblib"

    assert csv_path.exists(), "Validated dataset CSV must exist"
    assert artifact_path.exists(), "Trained model artifact joblib must exist"

    validation = validate_dataset(csv_path)
    assert validation["valid"] is True, validation
    assert validation["cv_family_leakage_count"] == 0
    assert validation["data_origins"] == {"controlled_synthetic": validation["rows"]}

    df = pd.read_csv(csv_path)
    assert len(df) >= 350
    assert df["program_family"].nunique() >= 50
    assert set(df["label"].unique()).issubset(set(ERROR_TAXONOMY))
    assert len(set(df["label"].unique())) == len(ERROR_TAXONOMY)

    bundle = joblib.load(artifact_path)
    pipe = bundle["pipeline"]
    sample = ExecutionSample(
        source_code=(
            "def total_range(a, b):\n"
            "    s = 0\n"
            "    for i in range(a, b):\n"
            "        s += i\n"
            "    return s\n"
        ),
        verdict="wrong_answer",
        stdout_actual="7",
        stdout_expected="12",
        passed_tests=0,
        total_tests=2,
    )
    doc = build_feature_document(sample)
    pred = pipe.predict([doc])[0]
    probs = pipe.predict_proba([doc])[0]
    assert pred in ERROR_TAXONOMY
    assert abs(float(sum(probs)) - 1.0) < 1e-5


def test_dataset_relabel_and_student_pii_sanitization(tmp_path: Path) -> None:
    sample_csv = tmp_path / "student_pending.csv"
    pd.DataFrame(
        [
            {
                "sample_id": "stu_sub_001",
                "program_family": "problem_sum_even",
                "label": "logic_error",
                "source_code": "def f(x):\n    return x > 0\n",
                "verdict": "wrong_answer",
                "passed_tests": 1,
                "total_tests": 3,
                "data_origin": "real_student_consented",
                "license": "ThinkFirst-Consented-Student-Data-v1",
                "review_status": "pending_human_label",
            }
        ]
    ).to_csv(sample_csv, index=False)

    val_before = validate_dataset(
        sample_csv, require_all_classes=False, min_families_for_cv=99
    )
    assert val_before["valid"] is True

    updated = relabel_sample(
        sample_csv,
        sample_id="stu_sub_001",
        new_label="condition_error",
        reviewer="instructor@thinkfirst.edu",
    )
    assert updated["old_label"] == "logic_error"
    assert updated["new_label"] == "condition_error"
    assert updated["review_status"] == "human_verified"

    cleaned = sanitize_source_code(
        "# contact alice@example.com or https://secret.local/a\nprint(1)"
    )
    assert "alice@example.com" not in cleaned
    assert "https://secret.local/a" not in cleaned
    assert "<redacted-email>" in cleaned
    assert "<redacted-url>" in cleaned

    pseudo1 = pseudonymize_student_id("user-123", "salt-a")
    pseudo2 = pseudonymize_student_id("user-123", "salt-a")
    pseudo3 = pseudonymize_student_id("user-123", "salt-b")
    assert pseudo1 == pseudo2
    assert pseudo1 != pseudo3
    assert "user-123" not in pseudo1


def test_multi_model_eval_report_and_external_benchmark() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    eval_path = repo_root / "ml" / "evaluation" / "eval_report_v1.json"
    assert eval_path.exists()
    report = json.loads(eval_path.read_text(encoding="utf-8"))
    assert report["family_leakage_count"] == 0
    assert len(report["models"]) >= 6
    assert report["selected_model"] in report["models"]
    assert report["cv_5fold_selected_macro_f1"]["mean"] >= 0.78


def test_rag_evaluation_default_threshold_022_and_multilanguage_ood_rejection() -> None:
    from ml.evaluation.evaluate_rag import run_rag_evaluation

    report = run_rag_evaluation()
    assert report["corpus_documents"] == 26
    assert report["corpus_chunks"] >= 45
    assert set(report["languages_covered"]) == {
        "c",
        "cpp",
        "java",
        "javascript",
        "python",
    }
    assert report["similarity_threshold"] == 0.22
    assert report["hit_at_1"] == 1.0
    assert report["hit_at_3"] == 1.0
    assert report["mrr"] == 1.0
    assert report["no_match_rejection_rate"] == 1.0
