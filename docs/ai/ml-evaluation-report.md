# ML Error Classifier Evaluation Report (`error-clf-v1.1.0`)

- **Dataset Version:** `python_errors_v1` (`data_origin = controlled_synthetic`)
- **Trained At (UTC):** `2026-11-28T17:14:03.535313+00:00`
- **Total Execution-Validated Samples:** `399` across `58` original Python program families
- **Split Strategy:** `StratifiedGroupKFold(n_splits=5, grouped by program_family)` (Train: `319` samples / `46` families; Held-Out Test: `80` samples / `12` families; Family Leakage: `0`)
- **Selected Model:** `TF-IDF + Calibrated LinearSVC` (Low-confidence threshold: `0.55`, top-2 ambiguity margin `< 0.12`)

> **Honesty & Data Provenance Notice:** Supervised training uses strictly separated execution-validated `controlled_synthetic` program mutations (`python_errors_v1.csv`). Real-world student generalization MUST NOT be claimed from synthetic metrics alone. Consent-gated real student debugging events are exported separately via `ml/tools/export_consented_student_dataset.py` and require human verification via `ml/tools/validate_and_label.py` before supervised retraining.

## 1. Multi-Algorithm Comparison (5-Fold Grouped CV + Held-Out Unseen Families)

| Model | 5-Fold CV Macro F1 | Holdout Macro F1 | Holdout Weighted F1 | `condition_error` F1 |
| :--- | :---: | :---: | :---: | :---: |
| Rule-Based Heuristic Baseline | 0.6454 ± 0.0368 | 0.6880 | 0.6694 | 0.3333 |
| TF-IDF + Logistic Regression | 0.8049 ± 0.0452 | 0.8597 | 0.8483 | 0.6087 |
| **TF-IDF + Calibrated LinearSVC (Selected)** | **0.8191 ± 0.0576** | **0.8936** | **0.8888** | **0.7692** |
| TF-IDF + Random Forest | 0.7882 ± 0.0265 | 0.8129 | 0.8043 | 0.6364 |
| TF-IDF + Extra Trees | 0.8185 ± 0.0351 | 0.8503 | 0.8438 | 0.7200 |
| TF-IDF + Complement Naive Bayes | 0.7937 ± 0.0219 | 0.8341 | 0.8302 | 0.7333 |

- **Selected Model 5-Fold CV Folds:** `[0.8936, 0.8786, 0.7482, 0.8035, 0.7718]` (Mean `0.8191` ± `0.0576`)

## 2. Per-Class Performance (TF-IDF + Calibrated LinearSVC, Held-Out Unseen Families)

| Error Class | Precision | Recall | F1 | Support |
| :--- | :---: | :---: | :---: | :---: |
| `syntax_error` | 1.0000 | 1.0000 | 1.0000 | 9 |
| `runtime_error` | 1.0000 | 1.0000 | 1.0000 | 10 |
| `indexing_error` | 1.0000 | 0.8750 | 0.9333 | 8 |
| `loop_boundary_error` | 0.8182 | 0.9000 | 0.8571 | 10 |
| `condition_error` | 0.8333 | 0.7143 | 0.7692 | 14 |
| `initialization_error` | 0.8889 | 0.8889 | 0.8889 | 9 |
| `function_return_error` | 1.0000 | 1.0000 | 1.0000 | 11 |
| `logic_error` | 0.6364 | 0.7778 | 0.7000 | 9 |

## 3. Confusion Matrix (Rows = True, Cols = Predicted)

| True \ Pred | syntax_error | runtime_error | indexing_error | loop_boundary_error | condition_error | initialization_error | function_return_error | logic_error |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `syntax_error` | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `runtime_error` | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| `indexing_error` | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 1 |
| `loop_boundary_error` | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 1 |
| `condition_error` | 0 | 0 | 0 | 1 | 10 | 1 | 0 | 2 |
| `initialization_error` | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 |
| `function_return_error` | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 |
| `logic_error` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 7 |

## 4. Independent External Public Benchmark (`jkoppel/QuixBugs`, MIT License)

- **Provenance:** `public_curated` (`jkoppel/QuixBugs`, license `MIT`), **0% overlap with training data**.
- **Execution-Validated Samples Evaluated:** `28`
- **Top-1 Accuracy (Unseen Algorithmic Domain):** `0.4286`
- **Top-3 Accuracy (Candidate Ranking):** `0.7143`
- **Low-Confidence Uncertainty Abstention Rate:** `0.6786`
- **High-Confidence Subset Accuracy:** `0.4444` (`9` high-confidence predictions)
- **Interpretation:** Independent out-of-domain external benchmark (harder DP/graph/sorting algorithms from QuixBugs MIT, never included in training). Demonstrates honest OOD generalization and uncertainty abstention.

## 5. Reproduction & Data Governance Commands

```bash
# 1. Regenerate & validate execution-verified controlled synthetic dataset
backend/.venv/Scripts/python.exe -m ml.preprocessing.generate_dataset
backend/.venv/Scripts/python.exe -m ml.tools.validate_and_label validate ml/datasets/python_errors_v1.csv

# 2. Import & validate independent MIT-licensed public benchmark (QuixBugs)
backend/.venv/Scripts/python.exe -m ml.tools.import_public_quixbugs
backend/.venv/Scripts/python.exe -m ml.tools.validate_and_label validate ml/datasets/public_curated_quixbugs_v1.csv --allow-subset

# 3. Train, cross-validate 6 candidates, and evaluate external benchmark
backend/.venv/Scripts/python.exe -m ml.training.train

# 4. Export opt-in consented student events for human review (strictly separated)
backend/.venv/Scripts/python.exe -m ml.tools.export_consented_student_dataset
```

## 6. Documented Limitations

- Controlled synthetic mutations cover 58 original beginner-to-intermediate Python problem families; real multi-fault student submissions or advanced algorithms may produce lower confidence and are explicitly flagged (`is_low_confidence = true`) with ranked top-3 candidates.
- Non-Python languages (JavaScript, C, C++, Java) honestly report `diagnosis_source = 'rule_based'` via deterministic compiler/traceback/AST diagnostics rather than extrapolating a Python-trained ML artifact.
