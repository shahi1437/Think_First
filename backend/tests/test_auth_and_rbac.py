import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jwt.algorithms import RSAAlgorithm

from app.api.v1.deps import get_identity_repository, get_jwt_verifier
from app.core.config import Settings
from app.core.security import SupabaseJWTVerifier
from app.main import create_app
from app.repositories.identity import AuditRecord, PreferencesRecord, UserRecord
from app.schemas.identity import (
    ExplanationLanguage,
    LearningGoal,
    PreferredLanguage,
    ProgrammingExperience,
    RecommendedEntryTrack,
    RoleName,
    StartingPreference,
)


@dataclass
class EphemeralRSAKeys:
    private_key: rsa.RSAPrivateKey
    jwk_public: dict[str, Any]
    kid: str


def _generate_ephemeral_keys(kid: str = "test-kid-1") -> EphemeralRSAKeys:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk_dict: dict[str, Any] = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk_dict["kid"] = kid
    jwk_dict["alg"] = "RS256"
    jwk_dict["use"] = "sig"
    return EphemeralRSAKeys(private_key=private_key, jwk_public=jwk_dict, kid=kid)


def _sign_token(
    *,
    keys: EphemeralRSAKeys,
    sub: UUID,
    email: str,
    issuer: str = "https://local.supabase.test/auth/v1",
    audience: str = "authenticated",
    expires_delta: timedelta = timedelta(minutes=30),
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(sub),
        "email": email,
        "iss": issuer,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        keys.private_key,
        algorithm="RS256",
        headers={"kid": keys.kid},
    )


class InMemoryIdentityRepository:
    """In-memory implementation of IdentityRepository for fast auth & RBAC verification."""

    def __init__(self) -> None:
        self.users: dict[UUID, UserRecord] = {}
        self.audit_logs: list[AuditRecord] = []

    def seed_user(
        self,
        *,
        user_id: UUID,
        email: str,
        roles: list[RoleName],
        full_name: str = "",
    ) -> UserRecord:
        record = UserRecord(
            id=user_id,
            email=email.lower(),
            full_name=full_name,
            avatar_url=None,
            roles=sorted(set(roles)),
            onboarding_completed=False,
            onboarding_completed_at=None,
            created_at=datetime.now(UTC),
            preferences=None,
        )
        self.users[user_id] = record
        return record

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        return self.users.get(user_id)

    async def ensure_student_profile(
        self, user_id: UUID, email: str, full_name: str = ""
    ) -> UserRecord:
        if user_id in self.users:
            return self.users[user_id]
        return self.seed_user(
            user_id=user_id,
            email=email,
            roles=["student"],
            full_name=full_name,
        )

    async def upsert_preferences(
        self,
        *,
        user_id: UUID,
        programming_experience: ProgrammingExperience,
        preferred_language: PreferredLanguage,
        learning_goal: LearningGoal,
        daily_practice_minutes: int,
        preferred_explanation_language: ExplanationLanguage,
        starting_preference: StartingPreference,
        recommended_entry_track: RecommendedEntryTrack,
        full_name: str | None = None,
        mark_onboarding_completed: bool = False,
    ) -> UserRecord:
        user = self.users[user_id]
        if full_name is not None:
            user.full_name = full_name.strip()
        if mark_onboarding_completed and not user.onboarding_completed:
            user.onboarding_completed = True
            user.onboarding_completed_at = datetime.now(UTC)
        user.preferences = PreferencesRecord(
            user_id=user_id,
            programming_experience=programming_experience,
            preferred_language=preferred_language,
            learning_goal=learning_goal,
            daily_practice_minutes=daily_practice_minutes,
            preferred_explanation_language=preferred_explanation_language,
            starting_preference=starting_preference,
            recommended_entry_track=recommended_entry_track,
        )
        return user

    async def list_users(self, *, limit: int, offset: int) -> tuple[list[UserRecord], int]:
        ordered = sorted(self.users.values(), key=lambda u: u.created_at, reverse=True)
        return ordered[offset : offset + limit], len(ordered)

    async def grant_role(
        self, *, user_id: UUID, role: RoleName, granted_by: UUID
    ) -> list[RoleName]:
        _ = granted_by
        user = self.users[user_id]
        if role not in user.roles:
            user.roles = sorted([*user.roles, role])
        return user.roles

    async def revoke_role(self, *, user_id: UUID, role: RoleName) -> list[RoleName]:
        user = self.users[user_id]
        user.roles = sorted([r for r in user.roles if r != role])
        return user.roles

    async def count_users_with_role(self, role: RoleName) -> int:
        return sum(1 for u in self.users.values() if role in u.roles)

    async def record_audit_log(self, event: AuditRecord) -> None:
        self.audit_logs.append(event)


@pytest.fixture
def rsa_keys() -> EphemeralRSAKeys:
    return _generate_ephemeral_keys()


@pytest.fixture
def identity_repo() -> InMemoryIdentityRepository:
    return InMemoryIdentityRepository()


@pytest.fixture
def auth_app(
    rsa_keys: EphemeralRSAKeys,
    identity_repo: InMemoryIdentityRepository,
) -> FastAPI:
    settings = Settings(
        app_env="test",
        supabase_url="https://local.supabase.test",
        supabase_jwt_audience="authenticated",
    )
    app = create_app(settings=settings)

    async def fake_jwks_fetcher(_url: str) -> dict[str, Any]:
        return {"keys": [rsa_keys.jwk_public]}

    verifier = SupabaseJWTVerifier(settings=settings, jwks_fetcher=fake_jwks_fetcher)
    app.dependency_overrides[get_jwt_verifier] = lambda: verifier
    app.dependency_overrides[get_identity_repository] = lambda: identity_repo
    return app


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def test_unauthenticated_requests_return_401(auth_client: AsyncClient) -> None:
    for method, path in [
        ("GET", "/api/v1/users/me"),
        ("PATCH", "/api/v1/users/me/preferences"),
        ("POST", "/api/v1/users/me/onboarding"),
        ("GET", "/api/v1/teacher/me"),
        ("GET", "/api/v1/admin/users"),
    ]:
        response = await auth_client.request(method, path)
        assert response.status_code == 401
        assert response.json()["code"] == "UNAUTHORIZED"


async def test_expired_and_wrong_issuer_tokens_rejected(
    auth_client: AsyncClient, rsa_keys: EphemeralRSAKeys
) -> None:
    user_id = uuid4()
    expired = _sign_token(
        keys=rsa_keys,
        sub=user_id,
        email="student@example.edu",
        expires_delta=timedelta(minutes=-5),
    )
    wrong_iss = _sign_token(
        keys=rsa_keys,
        sub=user_id,
        email="student@example.edu",
        issuer="https://evil.example.com/auth/v1",
    )
    tampered = _sign_token(keys=rsa_keys, sub=user_id, email="student@example.edu") + "tamper"

    for token in (expired, wrong_iss, tampered):
        response = await auth_client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401


async def test_jwt_metadata_cannot_grant_admin_or_teacher_role(
    auth_client: AsyncClient,
    rsa_keys: EphemeralRSAKeys,
) -> None:
    student_id = uuid4()
    token = _sign_token(
        keys=rsa_keys,
        sub=student_id,
        email="newlearner@example.edu",
        extra_claims={
            "user_metadata": {"full_name": "New Learner", "role": "admin"},
            "app_metadata": {"role": "admin"},
        },
    )

    me_response = await auth_client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["roles"] == ["student"]

    admin_response = await auth_client.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert admin_response.status_code == 403
    assert admin_response.json()["code"] == "FORBIDDEN"

    teacher_response = await auth_client.get(
        "/api/v1/teacher/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert teacher_response.status_code == 403


async def test_student_cannot_self_escalate_role_in_onboarding_or_preferences(
    auth_client: AsyncClient,
    rsa_keys: EphemeralRSAKeys,
    identity_repo: InMemoryIdentityRepository,
) -> None:
    student_id = uuid4()
    identity_repo.seed_user(user_id=student_id, email="s@example.edu", roles=["student"])
    token = _sign_token(keys=rsa_keys, sub=student_id, email="s@example.edu")

    response = await auth_client.patch(
        "/api/v1/users/me/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"preferred_language": "python", "role": "admin"},
    )
    assert response.status_code == 422
    assert identity_repo.users[student_id].roles == ["student"]


async def test_onboarding_persistence_and_track_recommendation(
    auth_client: AsyncClient,
    rsa_keys: EphemeralRSAKeys,
    identity_repo: InMemoryIdentityRepository,
) -> None:
    beginner_id = uuid4()
    identity_repo.seed_user(user_id=beginner_id, email="beginner@example.edu", roles=["student"])
    token = _sign_token(keys=rsa_keys, sub=beginner_id, email="beginner@example.edu")

    onboarding_resp = await auth_client.post(
        "/api/v1/users/me/onboarding",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Amina Rahman",
            "programming_experience": "none",
            "preferred_language": "python",
            "learning_goal": "school_fundamentals",
            "daily_practice_minutes": 25,
            "preferred_explanation_language": "bn",
            "starting_preference": "guided_beginner",
        },
    )
    assert onboarding_resp.status_code == 200
    data = onboarding_resp.json()
    assert data["onboarding_completed"] is True
    assert data["full_name"] == "Amina Rahman"
    assert data["preferences"]["recommended_entry_track"] == "foundation_lessons"

    # Simulate logout & re-login: GET /users/me returns persisted onboarding journey
    resume_resp = await auth_client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resume_resp.status_code == 200
    resumed = resume_resp.json()
    assert resumed["onboarding_completed"] is True
    assert resumed["preferences"]["daily_practice_minutes"] == 25
    assert resumed["preferences"]["recommended_entry_track"] == "foundation_lessons"

    # Update preferences later toward diagnostic track
    update_resp = await auth_client.patch(
        "/api/v1/users/me/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "programming_experience": "basic",
            "starting_preference": "diagnostic_assessment",
            "daily_practice_minutes": 45,
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["preferences"]["daily_practice_minutes"] == 45
    assert updated["preferences"]["recommended_entry_track"] == "diagnostic_assessment"


async def test_admin_can_grant_teacher_role_with_audit_log_and_last_admin_protected(
    auth_client: AsyncClient,
    rsa_keys: EphemeralRSAKeys,
    identity_repo: InMemoryIdentityRepository,
) -> None:
    admin_id = uuid4()
    teacher_candidate_id = uuid4()
    identity_repo.seed_user(user_id=admin_id, email="admin@example.edu", roles=["admin"])
    identity_repo.seed_user(
        user_id=teacher_candidate_id, email="prof@example.edu", roles=["student"]
    )

    admin_token = _sign_token(keys=rsa_keys, sub=admin_id, email="admin@example.edu")
    teacher_token = _sign_token(keys=rsa_keys, sub=teacher_candidate_id, email="prof@example.edu")

    # Before promotion, teacher route returns 403
    before = await auth_client.get(
        "/api/v1/teacher/me", headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert before.status_code == 403

    # Admin grants teacher role
    grant = await auth_client.post(
        f"/api/v1/admin/users/{teacher_candidate_id}/roles",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Request-ID": "req-admin-grant-001",
        },
        json={"role": "teacher"},
    )
    assert grant.status_code == 200
    assert grant.json()["roles"] == ["student", "teacher"]
    assert len(identity_repo.audit_logs) == 1
    assert identity_repo.audit_logs[0].action == "role.granted"
    assert identity_repo.audit_logs[0].request_id == "req-admin-grant-001"

    # After promotion, teacher route succeeds
    after = await auth_client.get(
        "/api/v1/teacher/me", headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert after.status_code == 200
    assert after.json()["authorized_scope"] == "teacher_courses"

    # Last admin cannot be stripped of admin role
    revoke_last_admin = await auth_client.delete(
        f"/api/v1/admin/users/{admin_id}/roles/admin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert revoke_last_admin.status_code == 409
    assert revoke_last_admin.json()["code"] == "LAST_ADMIN_PROTECTED"
