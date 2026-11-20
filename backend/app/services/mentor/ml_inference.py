"""FastAPI inference service for our own trained scikit-learn error classifier."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import joblib

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.mentor import MLCandidateScore, MLDiagnosisResponse

logger = get_logger(__name__)

# Ensure repository root is importable for shared `ml.preprocessing.features`
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml.preprocessing.features import (  # noqa: E402
    ERROR_TAXONOMY,
    ExecutionSample,
    build_feature_document,
)
from ml.training.baselines import RuleBasedErrorClassifier  # noqa: E402

DISPLAY_NAMES: dict[str, str] = {
    "syntax_error": "Syntax Error",
    "runtime_error": "Runtime Error",
    "indexing_error": "Indexing Error",
    "loop_boundary_error": "Loop Boundary Error",
    "condition_error": "Condition Error",
    "initialization_error": "Initialization Error",
    "function_return_error": "Function Return Error",
    "logic_error": "Logic Error",
}


class MLErrorClassifierService:
    """Loads versioned scikit-learn artifact and produces calibrated diagnoses with uncertainty."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bundle: dict[str, Any] | None = None
        self._load_attempted = False
        self._fallback = RuleBasedErrorClassifier()

    def _resolve_artifact_path(self) -> Path:
        configured = Path(self._settings.ml_model_artifact_path)
        if configured.is_absolute():
            return configured
        candidate_from_backend = (Path(__file__).resolve().parents[3] / configured).resolve()
        if candidate_from_backend.exists():
            return candidate_from_backend
        return (_REPO_ROOT / "ml" / "artifacts" / "error_classifier_v1.joblib").resolve()

    def _ensure_loaded(self) -> dict[str, Any] | None:
        if self._load_attempted:
            return self._bundle
        self._load_attempted = True
        artifact_path = self._resolve_artifact_path()
        if not artifact_path.exists():
            logger.warning("ml_artifact_missing", path=str(artifact_path))
            return None
        try:
            loaded = joblib.load(artifact_path)
            if isinstance(loaded, dict) and "pipeline" in loaded:
                self._bundle = loaded
                logger.info(
                    "ml_artifact_loaded",
                    model_version=loaded.get("model_version"),
                    holdout_macro_f1=loaded.get("holdout_macro_f1"),
                )
        except Exception as exc:
            logger.error("ml_artifact_load_failed", error_type=type(exc).__name__)
            self._bundle = None
        return self._bundle

    def warmup(self) -> bool:
        """Eagerly load the trained artifact at startup to avoid cold-start latency."""
        return self._ensure_loaded() is not None

    def predict(self, sample: ExecutionSample) -> MLDiagnosisResponse:
        bundle = self._ensure_loaded()
        threshold = self._settings.ml_low_confidence_threshold

        if bundle is None:
            # Explicit honest fallback if artifact missing
            pred = self._fallback.predict_one(sample)
            return MLDiagnosisResponse(
                model_version="rule-fallback-v1",
                predicted_error_code=pred,
                predicted_display_name=DISPLAY_NAMES.get(pred, pred),
                confidence=0.45,
                is_low_confidence=True,
                uncertainty_note=(
                    "Trained ML artifact was unavailable; diagnosis came from the deterministic "
                    "rule-based fallback and should be verified by tracing your code."
                ),
                top_candidates=[
                    MLCandidateScore(
                        error_code=pred,
                        display_name=DISPLAY_NAMES.get(pred, pred),
                        probability=0.45,
                    )
                ],
            )

        pipe = bundle["pipeline"]
        model_version = str(bundle.get("model_version", "error-clf-v1.0.0"))
        doc = build_feature_document(sample)
        probs = pipe.predict_proba([doc])[0]
        classes = list(pipe.classes_)

        ranked = sorted(
            zip(classes, probs, strict=True),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        top_code = str(ranked[0][0])
        top_prob = round(float(ranked[0][1]), 4)
        second_prob = round(float(ranked[1][1]), 4) if len(ranked) > 1 else 0.0
        margin = top_prob - second_prob

        # Flag low confidence if top probability below threshold OR close ambiguity between top-2
        is_low_conf = top_prob < threshold or margin < 0.12
        if is_low_conf:
            second_code = str(ranked[1][0]) if len(ranked) > 1 else top_code
            uncertainty_note = (
                f"Low confidence ({top_prob:.0%}). Signals overlap between "
                f"{DISPLAY_NAMES.get(top_code, top_code)} and "
                f"{DISPLAY_NAMES.get(second_code, second_code)}; trace the smallest failing test."
            )
        else:
            uncertainty_note = (
                f"Model confidence {top_prob:.0%} grounded in actual Judge0 execution evidence "
                "and AST structural cues."
            )

        candidates = [
            MLCandidateScore(
                error_code=str(code),
                display_name=DISPLAY_NAMES.get(str(code), str(code)),
                probability=round(float(prob), 4),
            )
            for code, prob in ranked[:3]
            if str(code) in ERROR_TAXONOMY
        ]

        return MLDiagnosisResponse(
            model_version=model_version,
            predicted_error_code=top_code,
            predicted_display_name=DISPLAY_NAMES.get(top_code, top_code),
            confidence=top_prob,
            is_low_confidence=is_low_conf,
            uncertainty_note=uncertainty_note,
            top_candidates=candidates,
        )
