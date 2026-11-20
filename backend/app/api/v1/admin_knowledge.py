"""Admin-only Verified RAG Knowledge Base management & retrieval diagnostics routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict

from app.api.v1.deps import get_rag_knowledge_service, require_roles
from app.repositories.identity import UserRecord
from app.schemas.mentor import (
    KnowledgeDocumentCreateRequest,
    KnowledgeDocumentResponse,
    KnowledgeStatus,
    RagSearchRequest,
    RagSearchResponse,
)
from app.services.mentor.rag_service import RagKnowledgeService

admin_knowledge_router = APIRouter(prefix="/admin/knowledge", tags=["Admin RAG Knowledge Base"])


class KnowledgeStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: KnowledgeStatus


class KnowledgeSeedResponse(BaseModel):
    seeded_documents: int


@admin_knowledge_router.get(
    "",
    response_model=list[KnowledgeDocumentResponse],
    summary="List all educational knowledge documents (draft, approved, archived)",
)
async def list_admin_knowledge_documents(
    _admin: UserRecord = Depends(require_roles("admin")),
    service: RagKnowledgeService = Depends(get_rag_knowledge_service),
) -> list[KnowledgeDocumentResponse]:
    return await service.list_documents(approved_only=False)


@admin_knowledge_router.post(
    "",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a knowledge document with semantic chunking & pgvector embeddings",
)
async def upsert_admin_knowledge_document(
    payload: KnowledgeDocumentCreateRequest,
    admin: UserRecord = Depends(require_roles("admin")),
    service: RagKnowledgeService = Depends(get_rag_knowledge_service),
) -> KnowledgeDocumentResponse:
    return await service.create_or_update_document(actor=admin, payload=payload)


@admin_knowledge_router.post(
    "/seed",
    response_model=KnowledgeSeedResponse,
    summary="Idempotently seed all 10 curated approved Python educational documents",
)
async def seed_approved_knowledge_corpus(
    admin: UserRecord = Depends(require_roles("admin")),
    service: RagKnowledgeService = Depends(get_rag_knowledge_service),
) -> KnowledgeSeedResponse:
    count = await service.seed_approved_corpus(actor_id=admin.id)
    return KnowledgeSeedResponse(seeded_documents=count)


@admin_knowledge_router.patch(
    "/{document_id}/status",
    response_model=KnowledgeDocumentResponse,
    summary="Approve, draft, or archive a knowledge document",
)
async def update_knowledge_document_status(
    document_id: UUID,
    payload: KnowledgeStatusUpdateRequest,
    admin: UserRecord = Depends(require_roles("admin")),
    service: RagKnowledgeService = Depends(get_rag_knowledge_service),
) -> KnowledgeDocumentResponse:
    return await service.set_document_status(
        actor=admin,
        document_id=document_id,
        new_status=payload.status,
    )


@admin_knowledge_router.post(
    "/search",
    response_model=RagSearchResponse,
    summary="Test pgvector RAG retrieval strictly against approved knowledge documents",
)
async def search_approved_knowledge_debug(
    payload: RagSearchRequest,
    _admin: UserRecord = Depends(require_roles("admin")),
    service: RagKnowledgeService = Depends(get_rag_knowledge_service),
) -> RagSearchResponse:
    return await service.retrieve(
        query=payload.query,
        topic=payload.topic,
        error_code=payload.error_code,
        top_k=payload.top_k,
    )
