"""Dataset validation and human-in-the-loop labeling CLI for Think_First ML pipelines.

Enforces strict separation between:
- controlled_synthetic (generated program-family mutations)
- public_curated (license-verified open-source benchmarks such as QuixBugs MIT)
- real_student_consented (anonymized opt-in student debugging events)

Usage:
  python -m ml.tools.validate_and_label validate ml/datasets/python_errors_v1.csv
  python -m ml.tools.validate_and_label list-pending ml/datasets/real_student_consented.csv
  python -m ml.tools.validate_and_label relabel ml/datasets/real_student_consented.csv \\
      --sample-id <id> --label condition_error --reviewer instructor@example.com
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from ml.preprocessing.features import ERROR_TAXONOMY

VALID_DATA_ORIGINS = frozenset(
    {"controlled_synthetic", "public_curated", "real_student_consented"}
)
VALID_REVIEW_STATUSES = frozenset(
    {"execution_validated", "pending_human_label", "human_verified", "rejected"}
)
REQUIRED_COLUMNS = (
    "sample_id",
    "program_family",
    "label",
    "source_code",
    "verdict",
    "passed_tests",
    "total_tests",
    "data_origin",
    "license",
    "review_status",
)


def validate_dataset(
    csv_path: Path,
    *,
    require_all_classes: bool = True,
    allow_mixed_origins: bool = False,
    min_families_for_cv: int = 5,
) -> dict[str, Any]:
    """Run schema, taxonomy, provenance, duplicate, and group-leakage checks on a dataset CSV."""
    errors: list[str] = []
    warnings: list[str] = []

    if not csv_path.exists():
        return {
            "valid": False,
            "errors": [f"File not found: {csv_path}"],
            "warnings": [],
        }

    df = pd.read_csv(csv_path)
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return {"valid": False, "errors": errors, "warnings": warnings}

    if len(df) == 0:
        warnings.append("Dataset contains 0 rows.")
        return {
            "valid": len(errors) == 0,
            "rows": 0,
            "errors": errors,
            "warnings": warnings,
        }

    # 1. Unique sample_id check
    dup_ids = int(df["sample_id"].duplicated().sum())
    if dup_ids > 0:
        errors.append(f"Found {dup_ids} duplicate sample_id values.")

    # 2. Label validity check
    invalid_labels = sorted(set(df["label"].astype(str)) - set(ERROR_TAXONOMY))
    if invalid_labels:
        errors.append(f"Invalid labels outside ERROR_TAXONOMY: {invalid_labels}")
    missing_classes = sorted(set(ERROR_TAXONOMY) - set(df["label"].astype(str)))
    if require_all_classes and missing_classes:
        errors.append(f"Missing taxonomy classes: {missing_classes}")
    elif missing_classes:
        warnings.append(f"Subset dataset omits classes: {missing_classes}")

    # 3. Provenance integrity (strict synthetic vs public vs real separation)
    origins = sorted(set(df["data_origin"].astype(str)))
    invalid_origins = sorted(set(origins) - VALID_DATA_ORIGINS)
    if invalid_origins:
        errors.append(f"Invalid data_origin values: {invalid_origins}")
    if not allow_mixed_origins and len(origins) > 1:
        errors.append(
            f"Mixed data_origin values in a single dataset file are disallowed: {origins}. "
            "Keep synthetic, public, and real student datasets strictly separated."
        )

    blank_licenses = int(
        df["license"].isna().sum() + (df["license"].astype(str).str.strip() == "").sum()
    )
    if blank_licenses > 0:
        errors.append(f"Found {blank_licenses} rows with missing license metadata.")

    invalid_review = sorted(
        set(df["review_status"].astype(str)) - VALID_REVIEW_STATUSES
    )
    if invalid_review:
        errors.append(f"Invalid review_status values: {invalid_review}")

    # 4. Exact code+verdict+stdout duplicate detection
    fingerprints = [
        hashlib.sha256(
            f"{row.get('source_code', '')}\n{row.get('verdict', '')}\n{row.get('stdout_actual', '')}".encode()
        ).hexdigest()
        for row in df.to_dict(orient="records")
    ]
    dup_content = len(fingerprints) - len(set(fingerprints))
    if dup_content > 0:
        warnings.append(
            f"Found {dup_content} duplicate (source_code, verdict, stdout_actual) rows."
        )

    # 5. Cross-family leakage verification under StratifiedGroupKFold
    unique_families = int(df["program_family"].nunique())
    leakage_count = 0
    if unique_families >= min_families_for_cv and len(df) >= min_families_for_cv:
        n_splits = min(5, unique_families)
        sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42)
        groups = df["program_family"].astype(str).tolist()
        labels = df["label"].astype(str).tolist()
        for tr_idx, te_idx in sgkf.split(df, labels, groups):
            tr_fams = {groups[i] for i in tr_idx}
            te_fams = {groups[i] for i in te_idx}
            leakage_count += len(tr_fams.intersection(te_fams))
        if leakage_count > 0:
            errors.append(
                f"Program family leakage detected across CV folds: {leakage_count}"
            )

    class_counts = {
        str(k): int(v) for k, v in df["label"].value_counts().sort_index().items()
    }
    origin_counts = {
        str(k): int(v) for k, v in df["data_origin"].value_counts().sort_index().items()
    }
    review_counts = {
        str(k): int(v)
        for k, v in df["review_status"].value_counts().sort_index().items()
    }

    return {
        "valid": len(errors) == 0,
        "path": str(csv_path),
        "rows": len(df),
        "unique_program_families": unique_families,
        "data_origins": origin_counts,
        "review_statuses": review_counts,
        "class_distribution": class_counts,
        "duplicate_content_rows": dup_content,
        "cv_family_leakage_count": leakage_count,
        "errors": errors,
        "warnings": warnings,
    }


def list_pending_rows(csv_path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    pending = df[df["review_status"] == "pending_human_label"].head(limit)
    results: list[dict[str, Any]] = []
    for row in pending.to_dict(orient="records"):
        results.append(
            {
                "sample_id": str(row["sample_id"]),
                "program_family": str(row["program_family"]),
                "proposed_label": str(row["label"]),
                "verdict": str(row["verdict"]),
                "exception_name": str(row.get("exception_name", "")),
                "source_preview": str(row["source_code"])[:160],
            }
        )
    return results


def relabel_sample(
    csv_path: Path,
    *,
    sample_id: str,
    new_label: str,
    reviewer: str,
    review_status: str = "human_verified",
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Update a sample's taxonomy label and review status with audit metadata."""
    if new_label not in ERROR_TAXONOMY:
        raise ValueError(f"Invalid label {new_label!r}. Allowed: {ERROR_TAXONOMY}")
    if review_status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"Invalid review_status {review_status!r}.")
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    mask = df["sample_id"].astype(str) == sample_id
    if not bool(mask.any()):
        raise KeyError(f"sample_id {sample_id!r} not found in {csv_path}")

    old_label = str(df.loc[mask, "label"].iloc[0])
    df.loc[mask, "label"] = new_label
    df.loc[mask, "review_status"] = review_status
    if "reviewed_by" not in df.columns:
        df["reviewed_by"] = ""
    if "reviewed_at" not in df.columns:
        df["reviewed_at"] = ""
    df.loc[mask, "reviewed_by"] = reviewer.strip()
    df.loc[mask, "reviewed_at"] = datetime.now(UTC).isoformat()

    target = output_path or csv_path
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False)
    return {
        "updated": True,
        "sample_id": sample_id,
        "old_label": old_label,
        "new_label": new_label,
        "review_status": review_status,
        "reviewer": reviewer.strip(),
        "output_path": str(target),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Think_First ML Dataset Validation & Human-in-the-Loop Labeling CLI"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate schema, provenance, and leakage.")
    p_val.add_argument("csv_path", type=Path)
    p_val.add_argument("--allow-subset", action="store_true")
    p_val.add_argument("--allow-mixed-origins", action="store_true")

    p_list = sub.add_parser(
        "list-pending", help="List samples awaiting human label review."
    )
    p_list.add_argument("csv_path", type=Path)
    p_list.add_argument("--limit", type=int, default=20)

    p_lbl = sub.add_parser("relabel", help="Relabel and verify a sample row.")
    p_lbl.add_argument("csv_path", type=Path)
    p_lbl.add_argument("--sample-id", required=True)
    p_lbl.add_argument("--label", required=True, choices=list(ERROR_TAXONOMY))
    p_lbl.add_argument("--reviewer", required=True)
    p_lbl.add_argument(
        "--status",
        default="human_verified",
        choices=sorted(VALID_REVIEW_STATUSES),
    )
    p_lbl.add_argument("--output", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        report = validate_dataset(
            args.csv_path,
            require_all_classes=not args.allow_subset,
            allow_mixed_origins=args.allow_mixed_origins,
        )
        print(json.dumps(report, indent=2))
        return 0 if report["valid"] else 1

    if args.cmd == "list-pending":
        rows = list_pending_rows(args.csv_path, limit=args.limit)
        print(json.dumps({"pending_count": len(rows), "samples": rows}, indent=2))
        return 0

    if args.cmd == "relabel":
        result = relabel_sample(
            args.csv_path,
            sample_id=args.sample_id,
            new_label=args.label,
            reviewer=args.reviewer,
            review_status=args.status,
            output_path=args.output,
        )
        print(json.dumps(result, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
