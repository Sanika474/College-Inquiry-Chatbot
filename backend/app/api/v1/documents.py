"""Document Link Management & Streaming Endpoints for CampusIQ.

Provides secure viewing, downloading, and cataloging of authentic institutional documents
(syllabi, academic calendars, lecture notes, question banks) stored in Knowledge_Base.
Guarantees path traversal prevention and verified document metadata.
"""

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.knowledge import KBDocument

router = APIRouter(prefix="/documents", tags=["Academic Documents"])


class PublicDocumentSchema(BaseModel):
    id: int
    title: str
    filename: str
    category: str
    program: Optional[str] = "MCA"
    semester: Optional[int] = None
    file_type: str
    file_size_bytes: int
    page_count: int
    view_url: str
    download_url: str


def _get_kb_dir() -> str:
    """Resolve validated Knowledge_Base directory path."""
    candidates = [
        os.path.join(os.getcwd(), "Knowledge_Base"),
        os.path.join(os.getcwd(), "College-Inquiry-Chatbot", "Knowledge_Base"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "Knowledge_Base"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isdir(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])


def _safe_resolve_path(filename: str) -> str:
    """Securely resolve file path inside Knowledge_Base, preventing path traversal."""
    kb_dir = _get_kb_dir()
    # Strip directory components to prevent traversal
    safe_name = os.path.basename(filename)
    resolved = os.path.abspath(os.path.join(kb_dir, safe_name))

    # Security check: must reside inside kb_dir
    if not resolved.startswith(kb_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Illegal file path traversal detected.",
        )

    if not os.path.exists(resolved):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document file '{safe_name}' not found on server storage.",
        )

    return resolved


@router.get("", response_model=List[PublicDocumentSchema], summary="List available academic documents")
def list_public_documents(
    category: Optional[str] = Query(None, description="Filter by category (syllabus, calendar, notes, question_bank)"),
    semester: Optional[int] = Query(None, description="Filter by semester (1 or 2)"),
    db: Session = Depends(get_db),
) -> List[PublicDocumentSchema]:
    """Retrieve catalog of verified academic documents with secure viewing and download URLs."""
    query = db.query(KBDocument)
    if category:
        query = query.filter(KBDocument.category.ilike(f"%{category}%"))

    docs = query.order_by(KBDocument.id.asc()).all()
    results = []

    for d in docs:
        sem = 1 if "sem 1" in d.filename.lower() or "ist sem" in d.filename.lower() else (2 if "sem 2" in d.filename.lower() else None)
        if semester and sem != semester:
            continue

        title = d.filename.replace(".pdf", "").replace(".docx", "").replace("_", " ")
        results.append(
            PublicDocumentSchema(
                id=d.id,
                title=title,
                filename=d.filename,
                category=d.category,
                program="MCA",
                semester=sem,
                file_type=d.file_type,
                file_size_bytes=d.file_size_bytes,
                page_count=d.page_count,
                view_url=f"/api/v1/documents/{d.id}/view",
                download_url=f"/api/v1/documents/{d.id}/download",
            )
        )

    return results


@router.get("/{doc_id}/view", summary="View document inline (in browser)")
def view_document_inline(doc_id: int, db: Session = Depends(get_db)):
    """Serve official document inline in browser (e.g. PDF viewer)."""
    doc = db.query(KBDocument).filter(KBDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} was not found.",
        )

    file_path = _safe_resolve_path(doc.filename)
    media_type = "application/pdf" if doc.file_type == ".pdf" else "application/octet-stream"

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/{doc_id}/download", summary="Download official document")
def download_document(doc_id: int, db: Session = Depends(get_db)):
    """Download official document file as an attachment."""
    doc = db.query(KBDocument).filter(KBDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} was not found.",
        )

    file_path = _safe_resolve_path(doc.filename)
    return FileResponse(
        file_path,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
        },
    )

