"""Shared AST + execution-evidence feature builder for ML training and inference.

Keeping feature extraction in a single pure-Python module guarantees zero
train/serve skew between `ml/training/train.py` and FastAPI inference.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

ERROR_TAXONOMY: tuple[str, ...] = (
    "syntax_error",
    "runtime_error",
    "indexing_error",
    "loop_boundary_error",
    "condition_error",
    "initialization_error",
    "function_return_error",
    "logic_error",
)

_EXCEPTION_RE = re.compile(r"([A-Za-z]+Error):")


@dataclass(frozen=True, slots=True)
class ExecutionSample:
    """Normalized input to the ML error classifier."""

    source_code: str
    verdict: str
    stderr: str = ""
    compile_output: str = ""
    stdout_actual: str = ""
    stdout_expected: str = ""
    passed_tests: int = 0
    total_tests: int = 1


def extract_exception_name(stderr: str, compile_output: str) -> str:
    combined = f"{compile_output}\n{stderr}"
    matches = _EXCEPTION_RE.findall(combined)
    return matches[-1] if matches else "none"


def _extract_ast_cues(source_code: str) -> list[str]:
    cues: list[str] = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        cues.append("ast_syntax_invalid")
        if exc.msg:
            msg_slug = re.sub(r"[^a-z0-9]+", "_", exc.msg.lower()).strip("_")
            cues.append(f"syntax_msg_{msg_slug[:40]}")
        return cues

    cues.append("ast_valid")

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
            if not returns:
                cues.append("fn_no_return")
            elif all(r.value is None for r in returns):
                cues.append("fn_empty_return")

            # Check if a print() is inside a function with no return
            has_print = any(
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "print"
                for n in ast.walk(node)
            )
            if has_print and not returns:
                cues.append("fn_prints_without_return")

            # Check for return directly inside loop body
            for child in ast.walk(node):
                if isinstance(child, (ast.For, ast.While)):
                    for stmt in child.body:
                        if isinstance(stmt, ast.Return):
                            cues.append("fn_direct_return_in_loop")
                        elif isinstance(stmt, ast.If) and (
                            any(isinstance(s, ast.Return) for s in stmt.orelse)
                            and any(isinstance(s, ast.Return) for s in stmt.body)
                        ):
                            cues.append("fn_both_branches_return_in_loop")

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "range":
                cues.append(f"range_argc_{len(node.args)}")
                for arg in node.args:
                    arg_src = ast.unparse(arg)
                    if "+ 1" in arg_src or "+1" in arg_src:
                        cues.append("range_has_plus_one")
                    if "- 1" in arg_src or "-1" in arg_src:
                        cues.append("range_has_minus_one")
                    if "len(" in arg_src:
                        cues.append("range_uses_len")
                    if arg_src == "1":
                        cues.append("range_starts_at_one")

        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, (int, float)
            ):
                val = node.value.value
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_l = target.id.lower()
                        if val == 0 and any(
                            k in name_l
                            for k in ("max", "best", "largest", "min", "small", "prod", "res", "ans")
                        ):
                            cues.append("init_zero_extremum_or_prod")
                        elif val == 1 and any(k in name_l for k in ("sum", "total", "count")):
                            cues.append("init_one_accumulator")
                        elif val == 0:
                            cues.append("init_zero_var")

        if isinstance(node, ast.Subscript):
            cues.append("uses_subscript")
            slice_src = ast.unparse(node.slice)
            if "len(" in slice_src:
                cues.append("subscript_uses_len")
            if "+ 1" in slice_src or "+1" in slice_src:
                cues.append("subscript_plus_one")
            if slice_src == "1":
                cues.append("subscript_const_one")
            if slice_src == "-1":
                cues.append("subscript_const_neg_one")

        if isinstance(node, ast.Compare):
            for op in node.ops:
                cues.append(f"cmp_{type(op).__name__.lower()}")

        if isinstance(node, ast.BoolOp):
            cues.append(f"boolop_{type(node.op).__name__.lower()}")

        if isinstance(node, ast.BinOp):
            cues.append(f"binop_{type(node.op).__name__.lower()}")

    return cues


def _extract_output_cues(actual: str, expected: str) -> list[str]:
    cues: list[str] = []
    act = actual.strip()
    exp = expected.strip()

    if not act and exp:
        cues.append("output_empty")
    if act == "None":
        cues.append("output_is_none")
    if act == "0" and exp != "0":
        cues.append("output_is_zero_mismatch")
    if act == "1" and exp not in ("1", ""):
        cues.append("output_is_one_mismatch")
    if act and exp:
        try:
            a_num = float(act)
            e_num = float(exp)
            diff = a_num - e_num
            if abs(diff) == 1.0:
                cues.append("numeric_off_by_one")
            elif a_num < e_num:
                cues.append("numeric_actual_smaller")
            elif a_num > e_num:
                cues.append("numeric_actual_larger")
            if a_num == 0 and e_num < 0:
                cues.append("actual_zero_expected_negative")
            if e_num != 0 and abs(a_num) == abs(e_num) and a_num == -e_num:
                cues.append("numeric_sign_flipped")
        except ValueError:
            a_lines = act.splitlines()
            e_lines = exp.splitlines()
            if len(a_lines) != len(e_lines):
                cues.append("line_count_mismatch")
            if len(act) == len(exp) - 1:
                cues.append("string_short_by_one")
            if act.lower() in ("true", "false") and exp.lower() in ("true", "false"):
                if act.lower() != exp.lower():
                    cues.append("boolean_inverted")
    return cues


def build_feature_document(sample: ExecutionSample) -> str:
    """Convert code + execution evidence into a rich text representation for TF-IDF."""
    exc_name = extract_exception_name(sample.stderr, sample.compile_output)
    ast_cues = _extract_ast_cues(sample.source_code)
    out_cues = _extract_output_cues(sample.stdout_actual, sample.stdout_expected)

    pass_ratio = "pass_none"
    if sample.total_tests > 0:
        if sample.passed_tests == sample.total_tests:
            pass_ratio = "pass_all"
        elif sample.passed_tests > 0:
            pass_ratio = "pass_partial"

    signal_tokens = [
        f"verdict_{sample.verdict}",
        f"exception_{exc_name.lower()}",
        pass_ratio,
        *ast_cues,
        *out_cues,
    ]
    # Weight execution & AST structural signals explicitly alongside code tokens
    weighted_signals = " ".join(signal_tokens * 2)
    stderr_clean = re.sub(r'File "[^"]+"', 'File "<script>"', sample.stderr)
    stderr_clean = re.sub(r"line \d+", "line N", stderr_clean)
    compile_clean = re.sub(r'File "[^"]+"', 'File "<script>"', sample.compile_output)

    return (
        f"{weighted_signals}\n"
        f"STDERR: {stderr_clean[:400]}\n"
        f"COMPILE: {compile_clean[:400]}\n"
        f"CODE:\n{sample.source_code}"
    )
