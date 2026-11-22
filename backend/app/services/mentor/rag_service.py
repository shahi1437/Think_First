"""Verified pgvector RAG ingestion, retrieval, and evaluation service.

Strictly retrieves ONLY `status = 'approved'` educational knowledge documents.
Never indexes or returns hidden Judge0 tests or private reference solutions.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import status

from app.core.config import Settings
from app.core.errors import AppError
from app.models.mentor import KnowledgeDocument
from app.repositories.identity import UserRecord
from app.repositories.mentor import MentorRepository
from app.schemas.mentor import (
    KnowledgeDocumentCreateRequest,
    KnowledgeDocumentResponse,
    KnowledgeStatus,
    RagCitation,
    RagSearchResponse,
)
from app.services.mentor.embeddings import LocalSemanticEmbedder
from app.services.mentor.knowledge_corpus import (
    ALL_APPROVED_KNOWLEDGE_DOCS,
    chunk_markdown_document,
)


def _to_doc_response(doc: KnowledgeDocument) -> KnowledgeDocumentResponse:
    return KnowledgeDocumentResponse(
        id=doc.id,
        slug=doc.slug,
        title=doc.title,
        language_slug=doc.language_slug,
        topic=doc.topic,
        error_codes=list(doc.error_codes),
        source_name=doc.source_name,
        source_version=doc.source_version,
        status=doc.status,
        chunk_count=len(doc.chunks),
        approved_at=doc.approved_at,
        updated_at=doc.updated_at,
    )


class RagKnowledgeService:
    """Manages approved knowledge ingestion, semantic chunking, pgvector retrieval, and citations."""

    def __init__(self, repository: MentorRepository, settings: Settings) -> None:
        self._repo = repository
        self._settings = settings
        self._embedder = LocalSemanticEmbedder(dimensions=settings.rag_embedding_dimensions)

    async def seed_approved_corpus(self, *, actor_id: UUID | None = None) -> int:
        """Idempotently ingest & embed all curated approved multi-language educational documents."""
        ingested = 0
        for doc in ALL_APPROVED_KNOWLEDGE_DOCS:
            raw_chunks = chunk_markdown_document(doc.content_md)
            embedded_chunks: list[tuple[int, str, str, list[float]]] = []
            for idx, (heading, body) in enumerate(raw_chunks):
                embed_input = (
                    f"Language: {doc.language_slug}\n{doc.title}\nTopic: {doc.topic}\n"
                    f"Errors: {' '.join(doc.error_codes)}\n{heading}\n{body}"
                )
                embedded_chunks.append((idx, heading, body, self._embedder.embed(embed_input)))

            await self._repo.upsert_knowledge_document(
                slug=doc.slug,
                title=doc.title,
                language_slug=doc.language_slug,
                topic=doc.topic,
                error_codes=list(doc.error_codes),
                source_name=doc.source_name,
                source_version=doc.source_version,
                content_md=doc.content_md,
                status="approved",
                approved_by=actor_id,
                chunks=embedded_chunks,
            )
            ingested += 1
        return ingested

    async def create_or_update_document(
        self,
        *,
        actor: UserRecord,
        payload: KnowledgeDocumentCreateRequest,
    ) -> KnowledgeDocumentResponse:
        raw_chunks = chunk_markdown_document(payload.content_md)
        if not raw_chunks:
            raise AppError(
                code="EMPTY_KNOWLEDGE_CHUNKS",
                message="Knowledge document must contain at least one non-empty section.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        embedded_chunks: list[tuple[int, str, str, list[float]]] = []
        for idx, (heading, body) in enumerate(raw_chunks):
            embed_input = (
                f"{payload.title}\nTopic: {payload.topic}\n"
                f"Errors: {' '.join(payload.error_codes)}\n{heading}\n{body}"
            )
            embedded_chunks.append((idx, heading, body, self._embedder.embed(embed_input)))

        saved = await self._repo.upsert_knowledge_document(
            slug=payload.slug,
            title=payload.title.strip(),
            language_slug=payload.language_slug,
            topic=payload.topic.strip().lower(),
            error_codes=payload.error_codes,
            source_name=payload.source_name.strip(),
            source_version=payload.source_version.strip(),
            content_md=payload.content_md,
            status=payload.status,
            approved_by=actor.id if payload.status == "approved" else None,
            chunks=embedded_chunks,
        )
        return _to_doc_response(saved)

    async def list_documents(
        self, *, approved_only: bool = False
    ) -> list[KnowledgeDocumentResponse]:
        docs = await self._repo.list_knowledge_documents(approved_only=approved_only)
        return [_to_doc_response(d) for d in docs]

    async def set_document_status(
        self, *, actor: UserRecord, document_id: UUID, new_status: KnowledgeStatus
    ) -> KnowledgeDocumentResponse:
        updated = await self._repo.update_knowledge_status(
            document_id=document_id, new_status=new_status, actor_id=actor.id
        )
        if updated is None:
            raise AppError(
                code="KNOWLEDGE_DOCUMENT_NOT_FOUND",
                message="Knowledge document not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return _to_doc_response(updated)

    async def retrieve(
        self,
        *,
        query: str,
        topic: str | None = None,
        error_code: str | None = None,
        language_slug: str | None = None,
        top_k: int = 3,
    ) -> RagSearchResponse:
        """Retrieve approved chunks via PostgreSQL pgvector cosine similarity + metadata boost."""
        enriched_query = query
        if language_slug:
            enriched_query += f" language:{language_slug}"
        if topic:
            enriched_query += f" topic:{topic}"
        if error_code:
            enriched_query += f" error:{error_code}"

        query_vec = self._embedder.embed(enriched_query)
        candidates = await self._repo.search_approved_chunks_pgvector(
            query_embedding=query_vec,
            limit=max(top_k * 4, 12),
            topic=topic,
            language_slug=language_slug,
        )

        # If knowledge base is still empty in a fresh local DB, return explicit no-match fallback
        if not candidates:
            return RagSearchResponse(
                query=query,
                matched=False,
                fallback_note=(
                    "No approved educational references matched this query in the knowledge base."
                ),
                citations=[],
            )

        scored: list[tuple[float, RagCitation]] = []
        threshold = self._settings.rag_similarity_threshold
        norm_topic = topic.lower() if topic else None

        for chunk, doc, raw_sim in candidates:
            score = raw_sim
            if error_code and error_code in (chunk.error_codes or []):
                score += 0.14
            if norm_topic and (chunk.topic.lower() == norm_topic or norm_topic in doc.slug.lower()):
                score += 0.08
            score = min(round(score, 4), 1.0)
            if raw_sim < threshold and score < (threshold + 0.12):
                continue

            scored.append(
                (
                    score,
                    RagCitation(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        document_slug=doc.slug,
                        source_title=doc.title,
                        source_name=doc.source_name,
                        source_version=doc.source_version,
                        topic=doc.topic,
                        heading=chunk.heading,
                        excerpt=chunk.content[:360],
                        similarity=round(raw_sim, 4),
                    ),
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [c for _, c in scored[:top_k]]

        if not selected:
            return RagSearchResponse(
                query=query,
                matched=False,
                fallback_note=(
                    "No approved educational reference exceeded the relevance threshold; "
                    "relying on execution evidence without fabricated citations."
                ),
                citations=[],
            )

        return RagSearchResponse(
            query=query,
            matched=True,
            fallback_note=None,
            citations=selected,
        )
