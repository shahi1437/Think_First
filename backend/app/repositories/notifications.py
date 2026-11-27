"""Async SQLAlchemy repository for public.user_notifications."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import desc, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import UserNotification
from app.schemas.identity import RoleName
from app.schemas.notifications import NotificationCategory


class NotificationRepository(Protocol):
    """Persistence contract for role-scoped in-app notifications."""

    async def upsert_notification_by_source_key(
        self,
        *,
        recipient_user_id: UUID,
        actor_user_id: UUID | None,
        recipient_role: RoleName,
        category: NotificationCategory,
        title: str,
        body: str,
        href: str | None,
        source_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    async def create_notification(
        self,
        *,
        recipient_user_id: UUID,
        actor_user_id: UUID | None,
        recipient_role: RoleName,
        category: NotificationCategory,
        title: str,
        body: str,
        href: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> UserNotification: ...

    async def list_notifications(
        self,
        *,
        recipient_user_id: UUID,
        role: RoleName | None = None,
        category: NotificationCategory | None = None,
        unread_only: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[UserNotification], int, int]: ...

    async def mark_read(
        self,
        *,
        recipient_user_id: UUID,
        notification_id: UUID,
    ) -> UserNotification | None: ...

    async def mark_all_read(
        self,
        *,
        recipient_user_id: UUID,
        role: RoleName | None = None,
    ) -> int: ...


class SQLAlchemyNotificationRepository:
    """PostgreSQL implementation of NotificationRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_notification_by_source_key(
        self,
        *,
        recipient_user_id: UUID,
        actor_user_id: UUID | None,
        recipient_role: RoleName,
        category: NotificationCategory,
        title: str,
        body: str,
        href: str | None,
        source_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        stmt = (
            pg_insert(UserNotification)
            .values(
                recipient_user_id=recipient_user_id,
                actor_user_id=actor_user_id,
                recipient_role=recipient_role,
                category=category,
                title=title,
                body=body,
                href=href,
                source_key=source_key,
                metadata_json=dict(metadata or {}),
                is_read=False,
            )
            .on_conflict_do_nothing(
                index_elements=[UserNotification.recipient_user_id, UserNotification.source_key],
                index_where=UserNotification.source_key.is_not(None),
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def create_notification(
        self,
        *,
        recipient_user_id: UUID,
        actor_user_id: UUID | None,
        recipient_role: RoleName,
        category: NotificationCategory,
        title: str,
        body: str,
        href: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> UserNotification:
        row = UserNotification(
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            recipient_role=recipient_role,
            category=category,
            title=title,
            body=body,
            href=href,
            source_key=None,
            metadata_json=dict(metadata or {}),
            is_read=False,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def list_notifications(
        self,
        *,
        recipient_user_id: UUID,
        role: RoleName | None = None,
        category: NotificationCategory | None = None,
        unread_only: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[UserNotification], int, int]:
        base = select(UserNotification).where(
            UserNotification.recipient_user_id == recipient_user_id
        )
        if role is not None:
            base = base.where(UserNotification.recipient_role == role)

        unread_stmt = (
            select(func.count())
            .select_from(UserNotification)
            .where(
                UserNotification.recipient_user_id == recipient_user_id,
                UserNotification.is_read.is_(False),
            )
        )
        if role is not None:
            unread_stmt = unread_stmt.where(UserNotification.recipient_role == role)
        unread_count = int((await self._session.execute(unread_stmt)).scalar_one())

        filtered = base
        if category is not None:
            filtered = filtered.where(UserNotification.category == category)
        if unread_only:
            filtered = filtered.where(UserNotification.is_read.is_(False))

        total_stmt = select(func.count()).select_from(filtered.subquery())
        total = int((await self._session.execute(total_stmt)).scalar_one())

        rows_stmt = filtered.order_by(desc(UserNotification.created_at)).limit(limit).offset(offset)
        items = list((await self._session.execute(rows_stmt)).scalars().all())
        return items, total, unread_count

    async def mark_read(
        self,
        *,
        recipient_user_id: UUID,
        notification_id: UUID,
    ) -> UserNotification | None:
        res = await self._session.execute(
            select(UserNotification).where(
                UserNotification.id == notification_id,
                UserNotification.recipient_user_id == recipient_user_id,
            )
        )
        row = res.scalar_one_or_none()
        if row is None:
            return None
        if not row.is_read:
            row.is_read = True
            row.read_at = datetime.now(UTC)
            await self._session.commit()
            await self._session.refresh(row)
        return row

    async def mark_all_read(
        self,
        *,
        recipient_user_id: UUID,
        role: RoleName | None = None,
    ) -> int:
        now = datetime.now(UTC)
        stmt = (
            update(UserNotification)
            .where(
                UserNotification.recipient_user_id == recipient_user_id,
                UserNotification.is_read.is_(False),
            )
            .values(is_read=True, read_at=now)
        )
        if role is not None:
            stmt = stmt.where(UserNotification.recipient_role == role)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return int(getattr(result, "rowcount", 0) or 0)
