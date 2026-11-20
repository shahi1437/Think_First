"""Safely bootstrap an initial authorized Admin account using trusted DB access.

Never guesses user emails, never stores hardcoded passwords, requires explicit
`--email` and `--confirm` flags, and writes an immutable `audit_logs` record.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sqlalchemy import text

from app.core.database import get_db_manager


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    prefix = local[:3] if len(local) >= 3 else local[:1]
    return f"{prefix}***@{domain}" if domain else f"{prefix}***"


def _validate_args(email: str, confirm: bool) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or len(normalized) < 5:
        raise ValueError("A valid registered account email must be provided via --email.")
    if not confirm:
        raise ValueError("Explicit --confirm flag is required before granting privileged roles.")
    return normalized


async def _bootstrap(
    *,
    email: str,
    grant_teacher: bool,
    allow_additional: bool,
    environment_label: str,
) -> int:
    db_manager = get_db_manager()
    try:
        async for session in db_manager.session():
            existing_admins = (
                await session.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM public.user_roles ur
                        JOIN public.profiles p ON p.id = ur.user_id
                        WHERE ur.role = 'admin'
                          AND p.email NOT LIKE '%@thinkfirst.test'
                          AND p.email NOT LIKE '%@codementor.%'
                          AND p.email NOT LIKE '%@example.%'
                        """
                    )
                )
            ).scalar_one()

            if existing_admins > 0 and not allow_additional:
                print(
                    f"[ABORT] {existing_admins} authorized Admin account(s) already exist. "
                    "Use Admin UI (/admin/audit) or pass --allow-additional explicitly.",
                    file=sys.stderr,
                )
                return 2

            profile = (
                await session.execute(
                    text(
                        """
                        SELECT id, email, full_name
                        FROM public.profiles
                        WHERE lower(email) = lower(:email)
                        LIMIT 1
                        """
                    ),
                    {"email": email},
                )
            ).first()

            if profile is None:
                print(
                    f"[ABORT] No registered account found for {_mask_email(email)}. "
                    "Register through /register first before bootstrapping Admin.",
                    file=sys.stderr,
                )
                return 1

            user_id = profile.id
            await session.execute(
                text(
                    """
                    INSERT INTO public.user_roles (user_id, role, granted_by)
                    VALUES (:user_id, 'admin', :user_id)
                    ON CONFLICT (user_id, role) DO NOTHING
                    """
                ),
                {"user_id": user_id},
            )
            granted_roles = ["admin"]

            if grant_teacher:
                await session.execute(
                    text(
                        """
                        INSERT INTO public.user_roles (user_id, role, granted_by)
                        VALUES (:user_id, 'teacher', :user_id)
                        ON CONFLICT (user_id, role) DO NOTHING
                        """
                    ),
                    {"user_id": user_id},
                )
                granted_roles.append("teacher")

            await session.execute(
                text(
                    """
                    INSERT INTO public.audit_logs (
                        actor_user_id, action, target_type, target_id, metadata
                    )
                    VALUES (
                        :user_id,
                        'role.bootstrap_admin',
                        'user',
                        CAST(:target_id AS text),
                        CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "target_id": str(user_id),
                    "metadata": json.dumps(
                        {
                            "source": "cli_bootstrap_first_admin",
                            "environment": environment_label,
                            "granted_roles": granted_roles,
                        }
                    ),
                },
            )
            await session.commit()
            print(
                f"[PASS] Bootstrapped {', '.join(granted_roles)} for {_mask_email(profile.email)} "
                f"(env={environment_label}) with immutable audit_logs entry."
            )
            return 0
    finally:
        await db_manager.dispose()
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explicitly bootstrap an authorized First Admin account cleanly."
    )
    parser.add_argument("--email", required=True, help="Exact registered account email.")
    parser.add_argument(
        "--grant-teacher",
        action="store_true",
        help="Optionally also grant explicit teacher role alongside admin.",
    )
    parser.add_argument(
        "--allow-additional",
        action="store_true",
        help="Allow bootstrap even when another non-test Admin already exists.",
    )
    parser.add_argument(
        "--environment",
        default="local",
        choices=("local", "staging", "production"),
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required confirmation flag acknowledging privileged role assignment.",
    )
    args = parser.parse_args()
    try:
        email = _validate_args(args.email, args.confirm)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    return asyncio.run(
        _bootstrap(
            email=email,
            grant_teacher=args.grant_teacher,
            allow_additional=args.allow_additional,
            environment_label=args.environment,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
