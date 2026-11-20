from pathlib import Path

import joblib
import pandas as pd

from ml.preprocessing.features import ERROR_TAXONOMY, ExecutionSample, build_feature_document


def test_dataset_and_model_artifact_exist_and_predict_valid_classes() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    csv_path = repo_root / "ml" / "datasets" / "python_errors_v1.csv"
    artifact_path = repo_root / "ml" / "artifacts" / "error_classifier_v1.joblib"

    assert csv_path.exists(), "Validated dataset CSV must exist"
    assert artifact_path.exists(), "Trained model artifact joblib must exist"

    df = pd.read_csv(csv_path)
    assert len(df) >= 250
    assert df["program_family"].nunique() >= 30
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
