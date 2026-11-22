"""Deterministic compiler/runtime-grounded error diagnosis for JavaScript, C, C++, and Java.

Pedagogical Honesty Invariant:
- Python submissions use our trained scikit-learn ML classifier (`diagnosis_source = "ml_classifier"`).
- JavaScript, C, C++, and Java use this deterministic rule-based engine
  (`diagnosis_source = "rule_based"`, `model_version = "rule-multilang-v1"`).
- We NEVER claim ML model predictions for languages without a trained/evaluated ML dataset.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from app.schemas.mentor import MLCandidateScore, MLDiagnosisResponse

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml.preprocessing.features import ExecutionSample  # noqa: E402

_DISPLAY_NAMES: dict[str, str] = {
    "syntax_error": "Syntax / Compilation Error",
    "runtime_error": "Runtime Error",
    "indexing_error": "Indexing / Bounds Error",
    "loop_boundary_error": "Loop Boundary Error",
    "condition_error": "Condition Error",
    "initialization_error": "Initialization Error",
    "function_return_error": "Function Return Error",
    "logic_error": "Logic Error",
}

_LANG_LABELS: dict[str, str] = {
    "javascript": "JavaScript (Node.js)",
    "c": "C (GCC)",
    "cpp": "C++ (GCC)",
    "java": "Java (OpenJDK)",
}


def _build_response(
    *,
    language_slug: str,
    primary_code: str,
    confidence: float,
    secondary_code: str,
    reason: str,
) -> MLDiagnosisResponse:
    lang_label = _LANG_LABELS.get(language_slug, language_slug)
    sec_prob = round(max(0.05, min(1.0 - confidence, 0.35)), 4)
    is_low = confidence < 0.60
    candidates = [
        MLCandidateScore(
            error_code=primary_code,
            display_name=_DISPLAY_NAMES.get(primary_code, primary_code),
            probability=round(confidence, 4),
        )
    ]
    if secondary_code != primary_code:
        candidates.append(
            MLCandidateScore(
                error_code=secondary_code,
                display_name=_DISPLAY_NAMES.get(secondary_code, secondary_code),
                probability=sec_prob,
            )
        )
    return MLDiagnosisResponse(
        model_version="rule-multilang-v1",
        diagnosis_source="rule_based",
        language_slug=language_slug,
        predicted_error_code=primary_code,
        predicted_display_name=_DISPLAY_NAMES.get(primary_code, primary_code),
        confidence=round(confidence, 4),
        is_low_confidence=is_low,
        uncertainty_note=(
            f"Deterministic rule-based diagnosis for {lang_label} (not an ML classifier): {reason}"
        ),
        top_candidates=candidates,
    )


def diagnose_non_python_submission(
    sample: ExecutionSample,
    language_slug: str,
) -> MLDiagnosisResponse:
    """Classify compiler, runtime, and logical mistakes for JS, C, C++, and Java honestly."""
    verdict = (sample.verdict or "").lower()
    compile_out = sample.compile_output or ""
    stderr = sample.stderr or ""
    combined_err = f"{compile_out}\n{stderr}".lower()
    code = sample.source_code or ""

    # 1. Compilation / Syntax errors
    if verdict == "compilation_error" or "syntaxerror" in combined_err:
        if "missing return statement" in combined_err:
            return _build_response(
                language_slug=language_slug,
                primary_code="function_return_error",
                confidence=0.88,
                secondary_code="syntax_error",
                reason="Compiler reported a missing return statement in a non-void method/function.",
            )
        if "not initialized" in combined_err or "might not have been initialized" in combined_err:
            return _build_response(
                language_slug=language_slug,
                primary_code="initialization_error",
                confidence=0.86,
                secondary_code="syntax_error",
                reason="Compiler flagged a variable used before initialization.",
            )
        return _build_response(
            language_slug=language_slug,
            primary_code="syntax_error",
            confidence=0.92,
            secondary_code="runtime_error",
            reason="Compiler or parser rejected syntax, missing delimiter, type mismatch, or undeclared identifier.",
        )

    # 2. Indexing / bounds exceptions
    if any(
        tok in combined_err
        for tok in (
            "arrayindexoutofbounds",
            "stringindexoutofbounds",
            "indexoutofbounds",
            "out_of_range",
            "segmentation fault",
            "sigsegv",
            "buffer overflow",
        )
    ):
        return _build_response(
            language_slug=language_slug,
            primary_code="indexing_error",
            confidence=0.88,
            secondary_code="runtime_error",
            reason="Runtime output indicates an out-of-bounds array/string index or invalid memory access.",
        )

    # 3. Other explicit runtime exceptions / crashes
    if verdict in ("runtime_error", "memory_limit_exceeded"):
        if any(
            tok in combined_err
            for tok in ("referenceerror", "is not defined", "nullpointerexception", "typeerror")
        ):
            return _build_response(
                language_slug=language_slug,
                primary_code="runtime_error",
                confidence=0.86,
                secondary_code="initialization_error",
                reason="Runtime exception indicates an undefined identifier, null dereference, or invalid type operation.",
            )
        return _build_response(
            language_slug=language_slug,
            primary_code="runtime_error",
            confidence=0.84,
            secondary_code="logic_error",
            reason="Sandbox reported a non-zero exit status or runtime exception in stderr.",
        )

    # 4. Time limit exceeded -> usually loop boundary or termination condition
    if verdict == "time_limit_exceeded":
        return _build_response(
            language_slug=language_slug,
            primary_code="loop_boundary_error",
            confidence=0.80,
            secondary_code="condition_error",
            reason="Execution exceeded time limit, commonly caused by a non-terminating loop condition or missing counter update.",
        )

    # 5. Wrong answer -> inspect deterministic structural & output cues
    actual = (sample.stdout_actual or "").strip()
    expected = (sample.stdout_expected or "").strip()

    if (actual in ("", "undefined", "null", "None")) and expected not in (
        "",
        "undefined",
        "null",
    ):
        return _build_response(
            language_slug=language_slug,
            primary_code="function_return_error",
            confidence=0.72,
            secondary_code="logic_error",
            reason="Program produced empty or undefined output while a concrete value was expected.",
        )

    # Numeric off-by-one or loop boundary cue
    has_for_loop = bool(re.search(r"\bfor\s*\(", code))
    if has_for_loop and re.search(r";\s*[a-zA-Z_]\w*\s*(<|<=|>|>=)\s*", code):
        try:
            act_num = float(actual)
            exp_num = float(expected)
            if act_num != exp_num and (abs(act_num - exp_num) <= max(abs(exp_num), 10.0)):
                return _build_response(
                    language_slug=language_slug,
                    primary_code="loop_boundary_error",
                    confidence=0.68,
                    secondary_code="logic_error",
                    reason="Output differs slightly from expected inside a bounded loop — check '<' vs '<=' and start/end bounds.",
                )
        except ValueError:
            pass

    if re.search(
        r"\b(max|best|largest|min|smallest|product|prod)\b\s*=\s*0\b", code, re.IGNORECASE
    ):
        return _build_response(
            language_slug=language_slug,
            primary_code="initialization_error",
            confidence=0.72,
            secondary_code="logic_error",
            reason="An extremum or product accumulator appears initialized to 0, which can fail on negative or multiplicative cases.",
        )

    if re.search(r"\bif\s*\(", code) and re.search(r"(<=|>=|<|>|&&|\|\||==|===|!=)", code):
        return _build_response(
            language_slug=language_slug,
            primary_code="condition_error",
            confidence=0.58,
            secondary_code="logic_error",
            reason="Wrong answer with conditional branching — verify comparison operators and boundary conditions.",
        )

    return _build_response(
        language_slug=language_slug,
        primary_code="logic_error",
        confidence=0.55,
        secondary_code="loop_boundary_error",
        reason="Output did not match expected test case; trace variable values step-by-step on the smallest failing input.",
    )
