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


_MAX_NAMES = ("max", "best", "largest", "high", "peak", "top")
_MIN_NAMES = ("min", "low", "small", "least", "lowest")
_PROD_NAMES = ("prod", "product", "fact", "factorial", "mul")
_ACCUM_NAMES = ("sum", "total", "count", "cnt", "c", "tally", "hits", "res", "ans")


def _extract_if_cues(
    if_node: ast.If, *, in_loop: bool, has_lower_call: bool
) -> list[str]:
    cues: list[str] = ["has_if_stmt"]
    if in_loop:
        cues.append("if_inside_loop")
    if if_node.orelse and any(isinstance(s, ast.If) for s in if_node.orelse):
        cues.append("has_elif_chain")

    for sub in ast.walk(if_node.test):
        if isinstance(sub, ast.BoolOp):
            cues.append(f"if_boolop_{type(sub.op).__name__.lower()}")
        elif isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.Not):
            cues.append("if_unary_not")
        elif isinstance(sub, ast.Compare):
            left_src = ast.unparse(sub.left).lower()
            if "%" in left_src:
                cues.append("if_has_mod")
            for op, comp in zip(sub.ops, sub.comparators, strict=False):
                op_name = type(op).__name__.lower()
                cues.append(f"if_cmp_{op_name}")
                comp_src = ast.unparse(comp).lower()
                if "%" in left_src and comp_src == "0":
                    if isinstance(op, ast.Eq):
                        cues.append("if_mod_eq_zero")
                    elif isinstance(op, ast.NotEq):
                        cues.append("if_mod_neq_zero")
                if comp_src == "0":
                    cues.append(f"if_cmp_zero_{op_name}")
                if (
                    isinstance(op, (ast.In, ast.NotIn))
                    and isinstance(comp, ast.Constant)
                    and isinstance(comp.value, str)
                    and not has_lower_call
                ):
                    cues.append("if_str_membership_case_sensitive")
                if any(k in comp_src or k in left_src for k in _MAX_NAMES) and isinstance(
                    op, (ast.Lt, ast.LtE)
                ):
                    cues.append("if_max_var_uses_lt")
                if any(k in comp_src or k in left_src for k in _MIN_NAMES) and isinstance(
                    op, (ast.Gt, ast.GtE)
                ):
                    cues.append("if_min_var_uses_gt")

    for stmt in if_node.body:
        if (
            isinstance(stmt, ast.Return)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, bool)
        ):
            cues.append("if_returns_bool")
    return cues


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
    has_lower_call = any(
        isinstance(n, ast.Attribute) and n.attr in ("lower", "upper", "casefold")
        for n in ast.walk(tree)
    )

    # Track nodes nested inside loops for context-sensitive cues
    loop_nested_ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            for stmt in node.body:
                for inner in ast.walk(stmt):
                    loop_nested_ids.add(id(inner))

            # Direct loop boundary analysis
            if isinstance(node, ast.For):
                if (
                    isinstance(node.iter, ast.Call)
                    and isinstance(node.iter.func, ast.Name)
                    and node.iter.func.id == "range"
                ):
                    args = node.iter.args
                    arg_srcs = [ast.unparse(a) for a in args]
                    if len(args) == 1:
                        s0 = arg_srcs[0]
                        if "- 1" in s0 or "-1" in s0:
                            cues.append("for_range_minus_one")
                        if "+ 1" in s0 or "+1" in s0:
                            if "len(" in s0:
                                cues.append("for_range_len_plus_one")
                            else:
                                cues.append("for_range_plus_one")
                        if "len(" not in s0 and "+ 1" not in s0 and "+1" not in s0:
                            cues.append("for_range_one_arg_no_len")
                    elif len(args) >= 2:
                        start_s, stop_s = arg_srcs[0], arg_srcs[1]
                        if start_s == "1":
                            cues.append("for_range_starts_one")
                        elif start_s == "0":
                            cues.append("for_range_starts_zero_two_args")
                        elif "+ 1" in start_s or "+1" in start_s:
                            cues.append("for_range_start_plus_one")
                        if "- 1" in stop_s or "-1" in stop_s:
                            cues.append("for_range_minus_one")
                        elif "+ 1" in stop_s or "+1" in stop_s:
                            if "len(" in stop_s:
                                cues.append("for_range_len_plus_one")
                            else:
                                cues.append("for_range_plus_one")
                        elif "len(" not in stop_s:
                            cues.append("for_range_two_arg_no_plus_one")
            elif isinstance(node, ast.While) and isinstance(node.test, ast.Compare):
                for op in node.test.ops:
                    cues.append(f"while_cmp_{type(op).__name__.lower()}")

            # Detect accumulator reset inside loop body (direct statement in loop)
            for stmt in node.body:
                if (
                    isinstance(stmt, ast.Assign)
                    and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, (int, float))
                    and stmt.value.value in (0, 1)
                ):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            name_l = target.id.lower()
                            if any(
                                k in name_l
                                for k in (*_ACCUM_NAMES, *_PROD_NAMES, *_MAX_NAMES)
                            ):
                                cues.append("init_const_inside_loop")

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
            if not returns:
                cues.append("fn_no_return")
            elif all(r.value is None for r in returns):
                cues.append("fn_empty_return")
            else:
                has_top_level_return = any(isinstance(s, ast.Return) for s in node.body)
                if not has_top_level_return:
                    cues.append("fn_missing_top_level_return")

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
                        elif isinstance(stmt, ast.If):
                            body_ret = any(isinstance(s, ast.Return) for s in stmt.body)
                            else_ret = any(
                                isinstance(s, ast.Return) for s in stmt.orelse
                            )
                            if body_ret and else_ret:
                                cues.append("fn_both_branches_return_in_loop")
                            elif body_ret:
                                cues.append("fn_conditional_return_in_loop")

        if isinstance(node, ast.If):
            cues.extend(
                _extract_if_cues(
                    node,
                    in_loop=id(node) in loop_nested_ids,
                    has_lower_call=has_lower_call,
                )
            )

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "range"
        ):
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

        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, (int, float))
        ):
            val = node.value.value
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name_l = target.id.lower()
                    if val == 0 and any(k in name_l for k in _PROD_NAMES):
                        cues.append("init_zero_prod")
                        cues.append("init_zero_extremum_or_prod")
                    elif val == 0 and any(
                        k in name_l
                        for k in (*_MAX_NAMES, *_MIN_NAMES, "res", "ans")
                    ):
                        cues.append("init_zero_extremum_or_prod")
                    elif val == 1 and any(k in name_l for k in _ACCUM_NAMES):
                        cues.append("init_one_accumulator")
                    elif val != 0 and any(
                        k in name_l for k in ("sum", "total", "count", "cnt")
                    ):
                        cues.append("init_nonzero_accumulator")
                    elif val == 0:
                        cues.append("init_zero_var")

        if isinstance(node, ast.AugAssign):
            op_name = type(node.op).__name__.lower()
            cues.append(f"augassign_{op_name}")
            if isinstance(node.op, ast.Add):
                if isinstance(node.value, ast.Constant) and node.value.value == 1:
                    cues.append("augassign_add_one")
                elif isinstance(node.value, ast.Constant) and isinstance(
                    node.value.value, (int, float)
                ):
                    cues.append("augassign_add_const_other")
                else:
                    cues.append("augassign_add_expr")

        if isinstance(node, ast.Subscript):
            cues.append("uses_subscript")
            slice_src = ast.unparse(node.slice)
            if "len(" in slice_src:
                cues.append("subscript_uses_len")
            if "+ 1" in slice_src or "+1" in slice_src:
                cues.append("subscript_plus_one")
            if "- 1" in slice_src or "-1" in slice_src:
                cues.append("subscript_minus_one")
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
            if a_num == 0 and e_num > 0:
                cues.append("actual_zero_expected_positive")
            if e_num != 0 and abs(a_num) == abs(e_num) and a_num == -e_num:
                cues.append("numeric_sign_flipped")
            if a_num != 0 and e_num != 0 and abs(e_num) >= 2 and abs(a_num) >= 2:
                ratio = max(abs(a_num), abs(e_num)) / min(abs(a_num), abs(e_num))
                if abs(ratio - round(ratio)) < 1e-6 and round(ratio) >= 2:
                    cues.append("numeric_ratio_exact_multiple")
        except ValueError:
            a_lines = act.splitlines()
            e_lines = exp.splitlines()
            if len(a_lines) != len(e_lines):
                cues.append("line_count_mismatch")
            a_tokens = act.split()
            e_tokens = exp.split()
            if len(e_tokens) >= 2:
                if len(a_tokens) == len(e_tokens) - 1:
                    cues.append("output_tokens_short_by_one")
                elif len(a_tokens) == len(e_tokens) and a_tokens != e_tokens:
                    cues.append("output_tokens_same_len_diff")
            if len(act) == len(exp) - 1:
                cues.append("string_short_by_one")
            if (
                act.lower() in ("true", "false")
                and exp.lower() in ("true", "false")
                and act.lower() != exp.lower()
            ):
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
