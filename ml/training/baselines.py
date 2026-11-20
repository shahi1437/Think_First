"""Deterministic rule-based baseline for Python error classification.

Used strictly as an honest benchmark against our trained scikit-learn models.
"""

from __future__ import annotations

import ast

from ml.preprocessing.features import ExecutionSample, extract_exception_name


class RuleBasedErrorClassifier:
    """Simple interpretable heuristic baseline distinguishing observable vs semantic bugs."""

    def predict_one(self, sample: ExecutionSample) -> str:
        exc = extract_exception_name(sample.stderr, sample.compile_output)

        if sample.verdict == "compilation_error" or exc in ("SyntaxError", "IndentationError"):
            return "syntax_error"

        if exc == "IndexError":
            return "indexing_error"

        if sample.verdict == "runtime_error" or exc != "none":
            return "runtime_error"

        # Semantic wrong_answer heuristics (expected to be weaker than learned TF-IDF + LogReg)
        if sample.stdout_actual.strip() == "None":
            return "function_return_error"

        try:
            tree = ast.parse(sample.source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
                    if not has_return:
                        return "function_return_error"
        except SyntaxError:
            return "syntax_error"

        code_lower = sample.source_code.lower()
        if "best = 0" in code_lower or "prod = 0" in code_lower or "low = 0" in code_lower:
            return "initialization_error"
        if "range(" in code_lower and ("len(" in code_lower or ", b)" in code_lower):
            return "loop_boundary_error"
        if "if " in code_lower and ("<=" in code_lower or ">=" in code_lower or "!=" in code_lower):
            return "condition_error"

        return "logic_error"

    def predict(self, samples: list[ExecutionSample]) -> list[str]:
        return [self.predict_one(s) for s in samples]
