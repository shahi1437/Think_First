"""Phase 10 pre-deployment security, Dockerfile, CI, and production config checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.bootstrap_first_admin import _mask_email, _validate_args
from scripts.prepare_production_content import PUBLIC_DEMO_PROBLEM_SLUGS

from app.core.config import Settings

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_production_readiness_validator_flags_unsafe_defaults() -> None:
    unsafe = Settings(app_env="production")
    warnings = unsafe.validate_production_readiness()
    assert len(warnings) == 4

    safe = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres:secret@db.example.supabase.co:5432/postgres",
        supabase_url="https://exampleproject.supabase.co",
        cors_origins=["https://codementor-ai.vercel.app"],
        judge0_base_url="https://judge0.internal.example.com",
    )
    assert safe.validate_production_readiness() == []


def test_backend_dockerfile_bundles_ml_and_dynamic_port() -> None:
    dockerfile = (_REPO_ROOT / "infrastructure" / "docker" / "backend.Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "COPY ml /app/ml" in dockerfile
    assert "ML_MODEL_ARTIFACT_PATH=/app/ml/artifacts/error_classifier_v1.joblib" in dockerfile
    assert "${PORT:-8000}" in dockerfile


def test_ci_workflow_enforces_npm_audit_without_fail_open() -> None:
    ci_yaml = (_REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "npm audit --omit=dev --audit-level=high || true" not in ci_yaml
    assert "npm audit --omit=dev --audit-level=high" in ci_yaml


def test_public_demo_problem_slugs_cover_seeded_demo_assessments() -> None:
    assert len(PUBLIC_DEMO_PROBLEM_SLUGS) == 6
    assert "sum-of-even-numbers" in PUBLIC_DEMO_PROBLEM_SLUGS
    assert "transfer-step-range-sum" in PUBLIC_DEMO_PROBLEM_SLUGS


def test_bootstrap_first_admin_requires_explicit_confirm_and_valid_email() -> None:
    with pytest.raises(ValueError, match="--confirm"):
        _validate_args("user@example.edu", confirm=False)
    with pytest.raises(ValueError, match="valid registered account email"):
        _validate_args("invalid", confirm=True)

    assert _validate_args("  Admin@University.EDU ", confirm=True) == "admin@university.edu"
    assert _mask_email("shahi@gmail.com") == "sha***@gmail.com"
