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
        self.audit_events_with_time: list[tuple[AuditRecord, datetime]] = []
        self.full_fold_queries: int = 0
        self.target_fold_queries: int = 0

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

    async def get_user_by_email(self, email: str) -> UserRecord | None:
        needle = email.strip().lower()
        for user in self.users.values():
            if user.email.lower() == needle:
                return user
        return None

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
        active_language_slug: PreferredLanguage | None = None,
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
            active_language_slug=active_language_slug or preferred_language,
            learning_goal=learning_goal,
            daily_practice_minutes=daily_practice_minutes,
            preferred_explanation_language=preferred_explanation_language,
            starting_preference=starting_preference,
            recommended_entry_track=recommended_entry_track,
        )
        return user

    async def list_users(
        self,
        *,
        limit: int,
        offset: int,
        role: RoleName | None = None,
        q: str | None = None,
    ) -> tuple[list[UserRecord], int]:
        filtered = list(self.users.values())
        if role is not None:
            filtered = [u for u in filtered if role in u.roles]
        if q and q.strip():
            needle = q.strip().lower()
            filtered = [
                u for u in filtered if needle in u.email.lower() or needle in u.full_name.lower()
            ]
        ordered = sorted(filtered, key=lambda u: u.created_at, reverse=True)
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
        self.audit_events_with_time.append((event, datetime.now(UTC)))

    async def list_audit_events_by_target_type(
        self, target_type: str, limit: int = 1000, offset: int = 0
    ) -> list[tuple[AuditRecord, datetime, str | None]]:
        self.full_fold_queries += 1
        out: list[tuple[AuditRecord, datetime, str | None]] = []
        for ev, ts in self.audit_events_with_time:
            if ev.target_type == target_type:
                actor = self.users.get(ev.actor_user_id) if ev.actor_user_id else None
                out.append((ev, ts, actor.email if actor else None))
        return out[offset : offset + limit]

    async def list_audit_events_for_target(
        self, target_type: str, target_id: str
    ) -> list[tuple[AuditRecord, datetime, str | None]]:
        self.target_fold_queries += 1
        out: list[tuple[AuditRecord, datetime, str | None]] = []
        for ev, ts in self.audit_events_with_time:
            if ev.target_type == target_type and ev.target_id == target_id:
                actor = self.users.get(ev.actor_user_id) if ev.actor_user_id else None
                out.append((ev, ts, actor.email if actor else None))
        return out


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


async def test_portal_verification_blocks_cross_role_login_and_audits_attempts(
    auth_client: AsyncClient,
    rsa_keys: EphemeralRSAKeys,
    identity_repo: InMemoryIdentityRepository,
) -> None:
    student_id = uuid4()
    teacher_id = uuid4()
    admin_id = uuid4()
    identity_repo.seed_user(
        user_id=student_id, email="stu@example.edu", roles=["student"], full_name="Stu"
    )
    identity_repo.seed_user(
        user_id=teacher_id, email="tch@example.edu", roles=["student", "teacher"], full_name="Tch"
    )
    identity_repo.seed_user(
        user_id=admin_id, email="adm@example.edu", roles=["student", "admin"], full_name="Adm"
    )

    stu_tok = _sign_token(keys=rsa_keys, sub=student_id, email="stu@example.edu")
    tch_tok = _sign_token(keys=rsa_keys, sub=teacher_id, email="tch@example.edu")
    adm_tok = _sign_token(keys=rsa_keys, sub=admin_id, email="adm@example.edu")

    # Matching portals succeed
    assert (
        await auth_client.post(
            "/api/v1/users/me/verify-portal",
            headers={"Authorization": f"Bearer {stu_tok}"},
            json={"portal": "student"},
        )
    ).status_code == 200
    assert (
        await auth_client.post(
            "/api/v1/users/me/verify-portal",
            headers={"Authorization": f"Bearer {tch_tok}"},
            json={"portal": "teacher"},
        )
    ).status_code == 200
    assert (
        await auth_client.post(
            "/api/v1/users/me/verify-portal",
            headers={"Authorization": f"Bearer {adm_tok}"},
            json={"portal": "admin"},
        )
    ).status_code == 200

    # Cross-role attempts denied with 403 and audited
    for tok, wrong_portal in [
        (stu_tok, "teacher"),
        (stu_tok, "admin"),
        (tch_tok, "student"),
        (tch_tok, "admin"),
        (adm_tok, "student"),
        (adm_tok, "teacher"),
    ]:
        resp = await auth_client.post(
            "/api/v1/users/me/verify-portal",
            headers={"Authorization": f"Bearer {tok}"},
            json={"portal": wrong_portal},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "PORTAL_ACCESS_DENIED"

    denied_events = [a for a in identity_repo.audit_logs if a.action == "auth.portal_denied"]
    assert len(denied_events) == 6

    # Admin directory filtering by role & search query
    teachers_res = await auth_client.get(
        "/api/v1/admin/users?role=teacher",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert teachers_res.status_code == 200
    assert [u["email"] for u in teachers_res.json()["items"]] == ["tch@example.edu"]

    search_res = await auth_client.get(
        "/api/v1/admin/users?q=stu@example",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert search_res.status_code == 200
    assert [u["email"] for u in search_res.json()["items"]] == ["stu@example.edu"]


async def test_teacher_management_existing_user_lookup_invite_accept_security_and_revocation(
    auth_client: AsyncClient,
    rsa_keys: EphemeralRSAKeys,
    identity_repo: InMemoryIdentityRepository,
) -> None:
    admin_id = uuid4()
    student_id = uuid4()
    other_student_id = uuid4()
    invited_teacher_id = uuid4()

    identity_repo.seed_user(
        user_id=admin_id,
        email="admin@thinkfirst.test",
        roles=["student", "admin"],
        full_name="Platform Admin",
    )
    identity_repo.seed_user(
        user_id=student_id,
        email="existing.user@thinkfirst.test",
        roles=["student"],
        full_name="Existing Candidate",
    )
    identity_repo.seed_user(
        user_id=other_student_id,
        email="intruder@thinkfirst.test",
        roles=["student"],
        full_name="Intruder Student",
    )

    adm_tok = _sign_token(keys=rsa_keys, sub=admin_id, email="admin@thinkfirst.test")
    stu_tok = _sign_token(keys=rsa_keys, sub=student_id, email="existing.user@thinkfirst.test")
    intruder_tok = _sign_token(
        keys=rsa_keys, sub=other_student_id, email="intruder@thinkfirst.test"
    )

    # 1. Student cannot call any Admin Teacher Management endpoints
    for method, path in [
        ("GET", "/api/v1/admin/teachers"),
        ("GET", "/api/v1/admin/teachers/lookup?email=new@thinkfirst.test"),
        ("POST", "/api/v1/admin/teachers/invitations"),
    ]:
        kwargs = {"json": {"email": "new@thinkfirst.test"}} if method == "POST" else {}
        res = await auth_client.request(
            method, path, headers={"Authorization": f"Bearer {stu_tok}"}, **kwargs
        )
        assert res.status_code == 403

    # 2. Case A: Admin looks up an existing user -> confirms & grants Teacher role
    lookup_existing = await auth_client.get(
        "/api/v1/admin/teachers/lookup?email=existing.user@thinkfirst.test",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert lookup_existing.status_code == 200
    assert lookup_existing.json()["status"] == "existing_user_not_teacher"
    assert lookup_existing.json()["can_grant_directly"] is True
    assert lookup_existing.json()["existing_user"]["id"] == str(student_id)

    # Attempting to create a new-user invitation for an existing account returns 409
    inv_existing = await auth_client.post(
        "/api/v1/admin/teachers/invitations",
        headers={"Authorization": f"Bearer {adm_tok}"},
        json={"email": "existing.user@thinkfirst.test"},
    )
    assert inv_existing.status_code == 409
    assert inv_existing.json()["code"] == "EXISTING_ACCOUNT_FOUND"

    # Grant Teacher role to existing account via authorized Admin API
    grant_resp = await auth_client.post(
        f"/api/v1/admin/users/{student_id}/roles",
        headers={"Authorization": f"Bearer {adm_tok}"},
        json={"role": "teacher"},
    )
    assert grant_resp.status_code == 200
    assert grant_resp.json()["roles"] == ["student", "teacher"]

    lookup_after_grant = await auth_client.get(
        "/api/v1/admin/teachers/lookup?email=existing.user@thinkfirst.test",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert lookup_after_grant.status_code == 200
    assert lookup_after_grant.json()["status"] == "active_teacher"

    # Promoted Teacher cannot access Admin endpoints or self-promote to Admin
    assert (
        await auth_client.get(
            "/api/v1/admin/teachers", headers={"Authorization": f"Bearer {stu_tok}"}
        )
    ).status_code == 403
    assert (
        await auth_client.post(
            f"/api/v1/admin/users/{student_id}/roles",
            headers={"Authorization": f"Bearer {stu_tok}"},
            json={"role": "admin"},
        )
    ).status_code == 403

    # 3. Case B: Admin looks up and invites a brand-new Teacher email
    new_email = "new.instructor@thinkfirst.test"
    lookup_new = await auth_client.get(
        f"/api/v1/admin/teachers/lookup?email={new_email}",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert lookup_new.status_code == 200
    assert lookup_new.json()["status"] == "not_found"
    assert lookup_new.json()["can_invite"] is True

    create_inv = await auth_client.post(
        "/api/v1/admin/teachers/invitations",
        headers={"Authorization": f"Bearer {adm_tok}"},
        json={"email": new_email, "full_name": "Dr. New Instructor"},
    )
    assert create_inv.status_code == 201
    inv_data = create_inv.json()
    inv_id = inv_data["invitation"]["id"]
    first_token = inv_data["invitation_token"]
    assert first_token and first_token.startswith("tfi_")
    assert inv_data["invitation"]["status"] == "pending"
    assert inv_data["invitation"]["delivery_status"] == "delivery_blocked"

    # 4. Duplicate pending invitation is blocked with 409 DUPLICATE_PENDING_INVITATION
    dup_inv = await auth_client.post(
        "/api/v1/admin/teachers/invitations",
        headers={"Authorization": f"Bearer {adm_tok}"},
        json={"email": new_email},
    )
    assert dup_inv.status_code == 409
    assert dup_inv.json()["code"] == "DUPLICATE_PENDING_INVITATION"

    # 5. Resending invitation rotates token and invalidates the old token
    resend_inv = await auth_client.post(
        f"/api/v1/admin/teachers/invitations/{inv_id}/resend",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert resend_inv.status_code == 200
    rotated_token = resend_inv.json()["invitation_token"]
    assert rotated_token and rotated_token != first_token
    assert resend_inv.json()["invitation"]["resend_count"] == 1

    # Old rotated token is rejected with 404 INVITATION_INVALID
    old_inspect = await auth_client.get(
        f"/api/v1/users/teacher-invitations/inspect?token={first_token}"
    )
    assert old_inspect.status_code == 404
    assert old_inspect.json()["code"] == "INVITATION_INVALID"

    # New rotated token inspects cleanly
    valid_inspect = await auth_client.get(
        f"/api/v1/users/teacher-invitations/inspect?token={rotated_token}"
    )
    assert valid_inspect.status_code == 200
    assert valid_inspect.json()["is_valid"] is True
    assert valid_inspect.json()["email"] == new_email

    # 6. Wrong user (email mismatch) cannot accept the invitation
    mismatch_accept = await auth_client.post(
        "/api/v1/users/me/accept-teacher-invitation",
        headers={"Authorization": f"Bearer {intruder_tok}"},
        json={"token": rotated_token},
    )
    assert mismatch_accept.status_code == 403
    assert mismatch_accept.json()["code"] == "INVITATION_EMAIL_MISMATCH"
    assert identity_repo.users[other_student_id].roles == ["student"]

    # 7. Invited Teacher registers/signs in with matching email and accepts invitation
    invited_tok = _sign_token(keys=rsa_keys, sub=invited_teacher_id, email=new_email)
    accept_res = await auth_client.post(
        "/api/v1/users/me/accept-teacher-invitation",
        headers={"Authorization": f"Bearer {invited_tok}"},
        json={"token": rotated_token},
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["user"]["roles"] == ["student", "teacher"]
    assert "admin" not in accept_res.json()["user"]["roles"]

    # Replay of already-accepted token is rejected with 409 INVITATION_ALREADY_USED
    replay_res = await auth_client.post(
        "/api/v1/users/me/accept-teacher-invitation",
        headers={"Authorization": f"Bearer {invited_tok}"},
        json={"token": rotated_token},
    )
    assert replay_res.status_code == 409
    assert replay_res.json()["code"] == "INVITATION_ALREADY_USED"

    # Accepted Teacher can now log in via Teacher Portal & access /api/v1/teacher/me
    assert (
        await auth_client.post(
            "/api/v1/users/me/verify-portal",
            headers={"Authorization": f"Bearer {invited_tok}"},
            json={"portal": "teacher"},
        )
    ).status_code == 200
    assert (
        await auth_client.get(
            "/api/v1/teacher/me",
            headers={"Authorization": f"Bearer {invited_tok}"},
        )
    ).status_code == 200

    # 8. Revoking active Teacher access removes Teacher portal & Teacher API access
    revoke_role_res = await auth_client.delete(
        f"/api/v1/admin/users/{invited_teacher_id}/roles/teacher",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert revoke_role_res.status_code == 200
    assert revoke_role_res.json()["roles"] == ["student"]
    assert (
        await auth_client.get(
            "/api/v1/teacher/me",
            headers={"Authorization": f"Bearer {invited_tok}"},
        )
    ).status_code == 403
    assert (
        await auth_client.post(
            "/api/v1/users/me/verify-portal",
            headers={"Authorization": f"Bearer {invited_tok}"},
            json={"portal": "teacher"},
        )
    ).status_code == 403

    # 9. Expired & Revoked invitation tokens are rejected
    rev_inv_create = await auth_client.post(
        "/api/v1/admin/teachers/invitations",
        headers={"Authorization": f"Bearer {adm_tok}"},
        json={"email": "revoke.me@thinkfirst.test"},
    )
    rev_inv_id = rev_inv_create.json()["invitation"]["id"]
    rev_inv_tok = rev_inv_create.json()["invitation_token"]

    revoke_inv_res = await auth_client.delete(
        f"/api/v1/admin/teachers/invitations/{rev_inv_id}",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert revoke_inv_res.status_code == 200
    assert revoke_inv_res.json()["invitation"]["status"] == "revoked"

    rev_user_tok = _sign_token(keys=rsa_keys, sub=uuid4(), email="revoke.me@thinkfirst.test")
    rev_accept = await auth_client.post(
        "/api/v1/users/me/accept-teacher-invitation",
        headers={"Authorization": f"Bearer {rev_user_tok}"},
        json={"token": rev_inv_tok},
    )
    assert rev_accept.status_code == 410
    assert rev_accept.json()["code"] == "INVITATION_REVOKED"

    # 10. Expired invitation is rejected with 410 INVITATION_EXPIRED
    from app.schemas.identity import TeacherInvitationCreateRequest
    from app.services.identity.service import IdentityService

    id_service = IdentityService(identity_repo)
    expired_mut = await id_service.create_teacher_invitation(
        actor=identity_repo.users[admin_id],
        payload=TeacherInvitationCreateRequest(
            email="expired.invite@thinkfirst.test", full_name="Expired Prof"
        ),
        request_id="req-exp-1",
        expires_at_override=datetime.now(UTC) - timedelta(hours=2),
    )
    assert expired_mut.invitation.status == "expired"
    exp_user_tok = _sign_token(keys=rsa_keys, sub=uuid4(), email="expired.invite@thinkfirst.test")
    exp_accept = await auth_client.post(
        "/api/v1/users/me/accept-teacher-invitation",
        headers={"Authorization": f"Bearer {exp_user_tok}"},
        json={"token": expired_mut.invitation_token},
    )
    assert exp_accept.status_code == 410
    assert exp_accept.json()["code"] == "INVITATION_EXPIRED"


async def test_teacher_invitation_no_duplicate_folds_no_truncation_and_pagination(
    auth_client: AsyncClient,
    rsa_keys: EphemeralRSAKeys,
    identity_repo: InMemoryIdentityRepository,
) -> None:
    """Verify Correction 4 invariants:
    1. create/resend/revoke mutations never execute duplicate full-table folds.
    2. Folding streams across >2,000 events with zero silent newest-event truncation.
    3. GET /api/v1/admin/teachers supports proper offset/limit pagination and totals.
    """
    admin_id = uuid4()
    identity_repo.seed_user(
        user_id=admin_id,
        email="admin.scale@thinkfirst.test",
        roles=["student", "admin"],
        full_name="Scale Admin",
    )
    adm_tok = _sign_token(keys=rsa_keys, sub=admin_id, email="admin.scale@thinkfirst.test")

    # 1. Verify no duplicate fold queries on create, resend, revoke
    identity_repo.full_fold_queries = 0
    identity_repo.target_fold_queries = 0

    created = await auth_client.post(
        "/api/v1/admin/teachers/invitations",
        headers={"Authorization": f"Bearer {adm_tok}"},
        json={"email": "first.teacher@thinkfirst.test", "full_name": "First Teacher"},
    )
    assert created.status_code == 201
    inv_id = created.json()["invitation"]["id"]
    assert identity_repo.full_fold_queries == 1  # single duplicate check, no post-write reload

    identity_repo.full_fold_queries = 0
    identity_repo.target_fold_queries = 0
    resent = await auth_client.post(
        f"/api/v1/admin/teachers/invitations/{inv_id}/resend",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert resent.status_code == 200
    assert resent.json()["invitation"]["resend_count"] == 1
    assert identity_repo.full_fold_queries == 0  # targeted lookup only
    assert identity_repo.target_fold_queries == 1

    identity_repo.full_fold_queries = 0
    identity_repo.target_fold_queries = 0
    revoked = await auth_client.delete(
        f"/api/v1/admin/teachers/invitations/{inv_id}",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["invitation"]["status"] == "revoked"
    assert identity_repo.full_fold_queries == 0  # targeted lookup only
    assert identity_repo.target_fold_queries == 1

    # 2. Seed >2,000 historical invitation events to prove zero silent truncation
    from app.services.identity.service import (
        TEACHER_INVITATION_TARGET_TYPE,
        hash_teacher_invite_token,
    )

    base_time = datetime.now(UTC) - timedelta(hours=3)
    for idx in range(2050):
        hist_id = uuid4()
        ev_time = base_time + timedelta(seconds=idx)
        identity_repo.audit_events_with_time.append(
            (
                AuditRecord(
                    actor_user_id=admin_id,
                    action="teacher.invitation_created",
                    target_type=TEACHER_INVITATION_TARGET_TYPE,
                    target_id=str(hist_id),
                    metadata={
                        "email": f"historical.{idx:04d}@thinkfirst.test",
                        "full_name": f"Historical {idx:04d}",
                        "token_hash": hash_teacher_invite_token(f"tfi_hist_token_{idx:08d}_xyz"),
                        "token_preview": "tfi_hist...xyz",
                        "delivery_status": "delivery_blocked",
                        "expires_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
                    },
                ),
                ev_time,
            )
        )

    # Create a brand-new invitation AFTER >2,050 prior events
    newest = await auth_client.post(
        "/api/v1/admin/teachers/invitations",
        headers={"Authorization": f"Bearer {adm_tok}"},
        json={"email": "newest.beyond2000@thinkfirst.test", "full_name": "Newest Prof"},
    )
    assert newest.status_code == 201
    newest_token = newest.json()["invitation_token"]

    # Newest invitation MUST NOT be truncated and MUST be inspectable
    inspect_newest = await auth_client.get(
        f"/api/v1/users/teacher-invitations/inspect?token={newest_token}"
    )
    assert inspect_newest.status_code == 200
    assert inspect_newest.json()["email"] == "newest.beyond2000@thinkfirst.test"
    assert inspect_newest.json()["is_valid"] is True

    # 3. Verify proper pagination (limit, offset, invitations_total, independent invitations_offset)
    page1 = await auth_client.get(
        "/api/v1/admin/teachers?limit=2&offset=0",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert page1.status_code == 200
    p1 = page1.json()
    assert p1["invitations_total"] == 2052  # 1 revoked + 2050 historical + 1 newest
    assert p1["invitations_limit"] == 2
    assert p1["invitations_offset"] == 0
    assert len(p1["invitations"]) == 2
    assert p1["invitations"][0]["email"] == "newest.beyond2000@thinkfirst.test"
    assert p1["pending_invitations_count"] == 2051

    page2 = await auth_client.get(
        "/api/v1/admin/teachers?limit=2&offset=2",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert page2.status_code == 200
    p2 = page2.json()
    assert p2["invitations_offset"] == 2
    assert len(p2["invitations"]) == 2
    assert p2["invitations"][0]["email"] != p1["invitations"][0]["email"]

    indep_page = await auth_client.get(
        "/api/v1/admin/teachers?limit=50&offset=0&invitations_limit=3&invitations_offset=1",
        headers={"Authorization": f"Bearer {adm_tok}"},
    )
    assert indep_page.status_code == 200
    ip = indep_page.json()
    assert ip["invitations_limit"] == 3
    assert ip["invitations_offset"] == 1
    assert len(ip["invitations"]) == 3
    assert ip["invitations"][0]["email"] == p1["invitations"][1]["email"]
