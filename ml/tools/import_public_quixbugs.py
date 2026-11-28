"""Automated public MIT-licensed Python bug benchmark importer (QuixBugs).

Verifies SPDX license (`MIT`) from `jkoppel/QuixBugs` via GitHub API, downloads
curated buggy Python programs and their official JSON test cases, validates every
sample via isolated `-I` subprocess execution with strict timeouts, and saves an
independent external evaluation benchmark (`ml/datasets/public_curated_quixbugs_v1.csv`).

Strictly separated from controlled synthetic data (`data_origin = 'public_curated'`).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from ml.preprocessing.features import ERROR_TAXONOMY, extract_exception_name

REPO_OWNER = "jkoppel"
REPO_NAME = "QuixBugs"
ALLOWED_SPDX_LICENSES = frozenset({"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"})

# Curated, human-verified taxonomy labels for QuixBugs Python single-line defects
# whose official JSON testcases have deterministic scalar/list inputs & outputs.
# Each label reflects the documented root cause of the single-line bug in jkoppel/QuixBugs.
QUIXBUGS_CURATED_LABELS: dict[str, tuple[str, str]] = {
    "bucketsort": ("logic_error", "sorting"),
    "find_first_in_sorted": ("loop_boundary_error", "searching"),
    "find_in_sorted": ("loop_boundary_error", "searching"),
    "flatten": ("function_return_error", "recursion"),
    "get_factors": ("function_return_error", "math"),
    "hanoi": ("logic_error", "recursion"),
    "is_valid_parenthesization": ("condition_error", "strings"),
    "kheapsort": ("loop_boundary_error", "sorting"),
    "knapsack": ("condition_error", "dynamic_programming"),
    "kth": ("logic_error", "searching"),
    "lcs_length": ("indexing_error", "dynamic_programming"),
    "levenshtein": ("logic_error", "dynamic_programming"),
    "lis": ("initialization_error", "dynamic_programming"),
    "longest_common_subsequence": ("logic_error", "dynamic_programming"),
    "max_sublist_sum": ("initialization_error", "dynamic_programming"),
    "mergesort": ("condition_error", "sorting"),
    "next_palindrome": ("indexing_error", "lists"),
    "next_permutation": ("condition_error", "lists"),
    "pascal": ("loop_boundary_error", "lists"),
    "possible_change": ("condition_error", "dynamic_programming"),
    "powerset": ("logic_error", "recursion"),
    "quicksort": ("condition_error", "sorting"),
    "rpn_eval": ("logic_error", "stacks"),
    "shunting_yard": ("logic_error", "stacks"),
    "sieve": ("condition_error", "math"),
    "subsequences": ("function_return_error", "recursion"),
    "to_base": ("logic_error", "math"),
    "wrap": ("function_return_error", "strings"),
}


def verify_github_license(client: httpx.Client) -> str:
    resp = client.get(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/license")
    resp.raise_for_status()
    spdx_id = str(resp.json().get("license", {}).get("spdx_id", "")).strip()
    if spdx_id not in ALLOWED_SPDX_LICENSES:
        raise RuntimeError(
            f"Refusing to import {REPO_OWNER}/{REPO_NAME}: unsupported license {spdx_id!r}"
        )
    return spdx_id


def _execute_quixbugs_program(
    source_code: str,
    func_name: str,
    test_cases: list[tuple[list[Any], Any]],
) -> tuple[str, str, str, str, int, int]:
    """Run QuixBugs buggy function against official JSON testcases in an isolated subprocess."""
    harness = (
        "import json, sys\n"
        f"{source_code}\n"
        "payload = json.loads(sys.stdin.read())\n"
        "args = payload['args']\n"
        "if not isinstance(args, list):\n"
        "    args = [args]\n"
        f"res = {func_name}(*args)\n"
        "print(json.dumps(res, default=str))\n"
    )
    passed = 0
    first_verdict = "accepted"
    first_stderr = ""
    first_actual = ""
    first_expected = ""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(harness)
        tmp_path = Path(tmp.name)

    try:
        for args, expected in test_cases:
            stdin_payload = json.dumps({"args": args})
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", str(tmp_path)],
                    input=stdin_payload,
                    text=True,
                    capture_output=True,
                    timeout=1.5,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                if first_verdict == "accepted":
                    first_verdict = "time_limit_exceeded"
                    first_stderr = "TimeoutExpired"
                continue

            if proc.returncode != 0:
                stderr = proc.stderr.strip()
                if first_verdict == "accepted":
                    if "SyntaxError:" in stderr or "IndentationError:" in stderr:
                        first_verdict = "compilation_error"
                    else:
                        first_verdict = "runtime_error"
                    first_stderr = stderr
                continue

            actual_raw = proc.stdout.strip()
            expected_raw = json.dumps(expected, default=str)
            try:
                actual_val = json.loads(actual_raw)
                matched = actual_val == expected
            except (json.JSONDecodeError, ValueError):
                matched = actual_raw == expected_raw

            if matched:
                passed += 1
            elif first_verdict == "accepted":
                first_verdict = "wrong_answer"
                first_actual = actual_raw[:300]
                first_expected = expected_raw[:300]
    finally:
        tmp_path.unlink(missing_ok=True)

    return (
        first_verdict,
        first_stderr,
        first_actual,
        first_expected,
        passed,
        len(test_cases),
    )


def import_quixbugs_benchmark(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_base = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/master"

    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    with httpx.Client(timeout=20.0) as client:
        spdx_license = verify_github_license(client)

        for prog_name, (label, topic) in sorted(QUIXBUGS_CURATED_LABELS.items()):
            if label not in ERROR_TAXONOMY:
                raise ValueError(f"Invalid taxonomy label {label!r} for {prog_name}")

            code_resp = client.get(f"{raw_base}/python_programs/{prog_name}.py")
            tc_resp = client.get(f"{raw_base}/json_testcases/{prog_name}.json")
            if code_resp.status_code != 200 or tc_resp.status_code != 200:
                skipped.append(
                    {
                        "program": prog_name,
                        "reason": f"http_status code={code_resp.status_code} tc={tc_resp.status_code}",
                    }
                )
                continue

            source_code = code_resp.text.strip() + "\n"
            test_cases: list[tuple[list[Any], Any]] = []
            for line in tc_resp.text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                pair = json.loads(stripped)
                if isinstance(pair, list) and len(pair) == 2:
                    raw_in, expected = pair
                    args = raw_in if isinstance(raw_in, list) else [raw_in]
                    test_cases.append((args, expected))

            if not test_cases:
                skipped.append({"program": prog_name, "reason": "no_json_testcases"})
                continue

            verdict, stderr, actual, expected, passed, total = (
                _execute_quixbugs_program(source_code, prog_name, test_cases)
            )
            if verdict in ("accepted", "time_limit_exceeded"):
                skipped.append(
                    {
                        "program": prog_name,
                        "reason": f"verdict={verdict}, passed={passed}/{total}",
                    }
                )
                continue

            exc_name = extract_exception_name(stderr, "")
            # Refine observable runtime exceptions honestly when QuixBugs triggers IndexError/RecursionError
            effective_label = label
            if exc_name == "IndexError" and label not in (
                "indexing_error",
                "loop_boundary_error",
            ):
                effective_label = "indexing_error"
            elif verdict == "runtime_error" and exc_name not in ("none", "IndexError"):
                effective_label = "runtime_error"

            rows.append(
                {
                    "sample_id": f"quixbugs__{prog_name}",
                    "program_family": f"quixbugs_{prog_name}",
                    "topic": topic,
                    "mutation": f"quixbugs_single_line_defect_{prog_name}",
                    "label": effective_label,
                    "source_code": source_code,
                    "verdict": verdict,
                    "exception_name": exc_name,
                    "stderr": stderr[:800],
                    "compile_output": "",
                    "stdout_actual": actual,
                    "stdout_expected": expected,
                    "passed_tests": passed,
                    "total_tests": total,
                    "data_origin": "public_curated",
                    "license": f"{spdx_license} ({REPO_OWNER}/{REPO_NAME})",
                    "review_status": "execution_validated",
                }
            )

    df = pd.DataFrame(rows)
    csv_path = output_dir / "public_curated_quixbugs_v1.csv"
    df.to_csv(csv_path, index=False)

    summary = {
        "dataset_version": "public_curated_quixbugs_v1",
        "source_repository": f"https://github.com/{REPO_OWNER}/{REPO_NAME}",
        "spdx_license": spdx_license,
        "data_origin": "public_curated",
        "validated_samples": len(df),
        "skipped_samples": len(skipped),
        "class_distribution": (
            {str(k): int(v) for k, v in df["label"].value_counts().sort_index().items()}
            if len(df) > 0
            else {}
        ),
        "skipped_details": skipped,
    }
    meta_path = output_dir / "public_curated_quixbugs_v1_metadata.json"
    meta_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parents[1] / "datasets"
    result = import_quixbugs_benchmark(out_dir)
    print(json.dumps(result, indent=2))
