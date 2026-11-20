# ML Error Classifier Evaluation Report (`error-clf-v1.0.0`)

- **Dataset Version:** `python_errors_v1`
- **Trained At (UTC):** `2026-11-20T05:33:41.434776+00:00`
- **Total Execution-Validated Samples:** `309` across `42` original Python program families
- **Split Strategy:** `StratifiedGroupKFold(n_splits=5, grouped by program_family)` (Train: `249` samples / `33` families; Held-Out Test: `60` samples / `9` families; Family Leakage: `0`)
- **Selected Model:** `TF-IDF (word + char n-grams + AST/execution cues) + Logistic Regression` (Low-confidence threshold: `0.55`)

## Model Comparison (Held-Out Unseen Program Families)

| Model | Macro F1 | Weighted F1 | Macro Precision | Macro Recall |
| :--- | :---: | :---: | :---: | :---: |
| Rule-Based Baseline | 0.5945 | 0.6438 | 0.6424 | 0.6223 |
| **TF-IDF + Logistic Regression (Selected)** | **0.7196** | **0.7487** | **0.7304** | **0.7285** |
| TF-IDF + Random Forest | 0.7222 | 0.7444 | 0.7312 | 0.7308 |

- **5-Fold Grouped CV Macro F1 (Logistic Regression):** Mean `0.7745` ± `0.057` (Folds: `[0.7196, 0.7805, 0.7076, 0.8009, 0.864]`)

## Per-Class Performance (TF-IDF + Logistic Regression, Held-Out Test)

| Error Class | Precision | Recall | F1 | Support |
| :--- | :---: | :---: | :---: | :---: |
| `syntax_error` | 1.0 | 1.0 | 1.0 | 9 |
| `runtime_error` | 1.0 | 0.8889 | 0.9412 | 9 |
| `indexing_error` | 0.8333 | 0.8333 | 0.8333 | 6 |
| `loop_boundary_error` | 0.4545 | 0.7143 | 0.5556 | 7 |
| `condition_error` | 0.3333 | 0.1667 | 0.2222 | 6 |
| `initialization_error` | 0.6667 | 0.8 | 0.7273 | 5 |
| `function_return_error` | 1.0 | 0.8 | 0.8889 | 10 |
| `logic_error` | 0.5556 | 0.625 | 0.5882 | 8 |

## Confusion Matrix (Rows = True, Cols = Predicted)

| True \ Pred | syntax_error | runtime_error | indexing_error | loop_boundary_error | condition_error | initialization_error | function_return_error | logic_error |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `syntax_error` | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `runtime_error` | 0 | 8 | 1 | 0 | 0 | 0 | 0 | 0 |
| `indexing_error` | 0 | 0 | 5 | 1 | 0 | 0 | 0 | 0 |
| `loop_boundary_error` | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 2 |
| `condition_error` | 0 | 0 | 0 | 2 | 1 | 1 | 0 | 2 |
| `initialization_error` | 0 | 0 | 0 | 0 | 1 | 4 | 0 | 0 |
| `function_return_error` | 0 | 0 | 0 | 2 | 0 | 0 | 8 | 0 |
| `logic_error` | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 5 |

## Reproduction Commands

```bash
# From Think_First repository root using backend virtualenv
backend/.venv/Scripts/python.exe -m ml.preprocessing.generate_dataset
backend/.venv/Scripts/python.exe -m ml.training.train
```

## Documented Limitations

- Dataset covers 40 original beginner-to-basic Python problem families with controlled single-fault mutations; multi-fault student submissions or unseen algorithmic paradigms may yield lower confidence and are explicitly flagged (`is_low_confidence = true`) rather than presented as certain.
- Directly observable syntax and runtime exceptions are easier to separate than overlapping semantic mistakes (`condition_error` vs `logic_error`).
