"""Admin Knowledge Base Management Endpoints for CampusIQ."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.chatbot.ingestion import KnowledgeIngestionPipeline
from app.chatbot.retrieval import KnowledgeRetriever
from app.db.session import get_db
from app.models.knowledge import KBChunk, KBDocument, KBIngestionJob
from app.models.user import User

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base Administration"])


class DocumentSummarySchema(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size_bytes: int
    checksum: str
    page_count: int
    chunk_count: int
    ingestion_status: str
    error_message: Optional[str] = None
    category: str


class DocumentDetailSchema(DocumentSummarySchema):
    doc_metadata: Optional[Dict[str, Any]] = None
    chunks_preview: List[Dict[str, Any]] = []


class KBStatsSchema(BaseModel):
    total_documents: int
    indexed_documents: int
    scanned_documents: int
    error_documents: int
    total_chunks: int
    total_tokens: int


class ReindexResponseSchema(BaseModel):
    status: str
    job_id: str
    total_files: int
    processed_files: int
    skipped_files: int
    failed_files: int


@router.get(
    "/stats",
    response_model=KBStatsSchema,
    summary="Get Knowledge Base repository statistics",
)
def get_knowledge_stats(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return high-level statistics about ingested documents and indexed chunks."""
    total_docs = db.query(func.count(KBDocument.id)).scalar() or 0
    indexed_docs = (
        db.query(func.count(KBDocument.id))
        .filter(KBDocument.ingestion_status == "indexed")
        .scalar()
        or 0
    )
    scanned_docs = (
        db.query(func.count(KBDocument.id))
        .filter(KBDocument.ingestion_status == "scanned_ocr_required")
        .scalar()
        or 0
    )
    error_docs = (
        db.query(func.count(KBDocument.id))
        .filter(KBDocument.ingestion_status == "error")
        .scalar()
        or 0
    )
    total_chunks = db.query(func.count(KBChunk.id)).scalar() or 0
    total_tokens = db.query(func.sum(KBChunk.token_count)).scalar() or 0

    return {
        "total_documents": total_docs,
        "indexed_documents": indexed_docs,
        "scanned_documents": scanned_docs,
        "error_documents": error_docs,
        "total_chunks": total_chunks,
        "total_tokens": int(total_tokens),
    }


@router.get(
    "/documents",
    response_model=List[DocumentSummarySchema],
    summary="List all Knowledge Base documents",
)
def list_knowledge_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all registered institutional documents in the Knowledge_Base repository."""
    query = db.query(KBDocument).order_by(KBDocument.filename.asc())
    if status_filter:
        query = query.filter(KBDocument.ingestion_status == status_filter)

    docs = query.all()
    return [
        DocumentSummarySchema(
            id=d.id,
            filename=d.filename,
            file_type=d.file_type,
            file_size_bytes=d.file_size_bytes,
            checksum=d.checksum,
            page_count=d.page_count,
            chunk_count=d.chunk_count,
            ingestion_status=d.ingestion_status,
            error_message=d.error_message,
            category=d.category,
        )
        for d in docs
    ]


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentDetailSchema,
    summary="Get document details and chunk previews",
)
def get_knowledge_document_detail(
    doc_id: int,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve detailed metadata and chunk passages for a specific document."""
    doc = db.query(KBDocument).filter(KBDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} not found in knowledge base.",
        )

    chunks = (
        db.query(KBChunk)
        .filter(KBChunk.document_id == doc.id)
        .order_by(KBChunk.chunk_index.asc())
        .limit(10)
        .all()
    )

    chunks_preview = [
        {
            "id": c.id,
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "section_heading": c.section_heading,
            "token_count": c.token_count,
            "content_snippet": c.content[:300] + "..." if len(c.content) > 300 else c.content,
        }
        for c in chunks
    ]

    return DocumentDetailSchema(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        checksum=doc.checksum,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        ingestion_status=doc.ingestion_status,
        error_message=doc.error_message,
        category=doc.category,
        doc_metadata=doc.doc_metadata,
        chunks_preview=chunks_preview,
    )


@router.post(
    "/reindex",
    response_model=ReindexResponseSchema,
    summary="Trigger idempotent knowledge base re-ingestion",
)
def trigger_knowledge_reindex(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Execute ingestion pass over the Knowledge_Base folder. Unchanged files are skipped."""
    pipeline = KnowledgeIngestionPipeline(db)
    summary = pipeline.run_ingestion()
    return ReindexResponseSchema(
        status="completed",
        job_id=summary.job_id,
        total_files=summary.total_discovered,
        processed_files=summary.indexed_count,
        skipped_files=summary.skipped_count,
        failed_files=summary.failed_count,
    )


@router.get(
    "/search",
    summary="Admin testing tool for knowledge chunk retrieval",
)
def test_chunk_search(
    q: str = Query(..., description="Query phrase or keywords"),
    subject: Optional[str] = Query(None, description="Optional subject filter"),
    semester: Optional[int] = Query(None, description="Optional semester 1 or 2"),
    limit: int = Query(5, ge=1, le=20),
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Test retrieval rankings, scores, and chunk citations for any query."""
    retriever = KnowledgeRetriever(db)
    results = retriever.search_knowledge_chunks(
        query=q, subject=subject, semester=semester, limit=limit
    )
    return {
        "query": q,
        "subject": subject,
        "semester": semester,
        "matched_count": len(results),
        "results": results,
    }
