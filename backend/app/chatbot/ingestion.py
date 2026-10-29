"""Knowledge Base Ingestion Pipeline for CampusIQ.

Discovers documents in Knowledge_Base/, extracts text, detects scanned PDFs,
generates idempotent SHA-256 checksums, chunks passages, and stores records in PostgreSQL.
"""

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.chatbot.chunking import TextChunker
from app.chatbot.document_extractors import DocumentExtractor
from app.models.knowledge import KBChunk, KBDocument, KBIngestionJob

logger = logging.getLogger("campusiq.knowledge_ingestion")


class IngestionSummary:
    """Summary of a knowledge ingestion execution."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.total_discovered: int = 0
        self.indexed_count: int = 0
        self.skipped_count: int = 0
        self.scanned_count: int = 0
        self.failed_count: int = 0
        self.total_chunks_created: int = 0
        self.document_summaries: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "total_discovered": self.total_discovered,
            "indexed_count": self.indexed_count,
            "skipped_count": self.skipped_count,
            "scanned_count": self.scanned_count,
            "failed_count": self.failed_count,
            "total_chunks_created": self.total_chunks_created,
            "documents": self.document_summaries,
        }


class KnowledgeIngestionPipeline:
    """Orchestrates document discovery, extraction, chunking, and persistence."""

    def __init__(self, db: Session, kb_dir: Optional[str] = None):
        self.db = db
        # Resolve Knowledge_Base directory location
        if kb_dir and os.path.exists(kb_dir):
            self.kb_dir = kb_dir
        else:
            # Check current working directory, workspace root, and parent directories
            candidates = [
                os.path.join(os.getcwd(), "Knowledge_Base"),
                os.path.join(os.getcwd(), "Knowledge_base"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "Knowledge_Base"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Knowledge_Base"),
            ]
            self.kb_dir = next((c for c in candidates if os.path.exists(c)), candidates[0])

        self.chunker = TextChunker(
            target_chunk_words=220,
            min_chunk_words=30,
            max_chunk_words=420,
            overlap_words=25,
        )

    def run_ingestion(self, force_reprocess: bool = False) -> IngestionSummary:
        """Run the full idempotent ingestion pipeline across the Knowledge_Base folder."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        summary = IngestionSummary(job_id=job_id)

        job_record = KBIngestionJob(
            job_id=job_id,
            status="running",
            total_files=0,
            processed_files=0,
            skipped_files=0,
            failed_files=0,
        )
        self.db.add(job_record)
        self.db.commit()

        if not os.path.exists(self.kb_dir):
            msg = f"Knowledge base directory does not exist: {self.kb_dir}"
            logger.warning(msg)
            job_record.status = "failed"
            job_record.error_summary = msg
            job_record.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return summary

        # 1. Discover files
        discovered_files = [
            f
            for f in sorted(os.listdir(self.kb_dir))
            if os.path.isfile(os.path.join(self.kb_dir, f))
            and not f.startswith(".")
        ]
        summary.total_discovered = len(discovered_files)
        job_record.total_files = len(discovered_files)
        self.db.commit()

        logger.info(
            f"[KB Ingestion] Job {job_id} discovered {len(discovered_files)} files in {self.kb_dir}"
        )

        for filename in discovered_files:
            file_path = os.path.join(self.kb_dir, filename)
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(filename)[1].lower()

            # Compute content checksum for idempotency
            file_checksum = self._compute_file_checksum(file_path)
            category = self._infer_category(filename)

            # Check if unchanged document already exists
            existing_doc = (
                self.db.query(KBDocument)
                .filter(KBDocument.filename == filename)
                .first()
            )

            if (
                existing_doc
                and existing_doc.checksum == file_checksum
                and not force_reprocess
            ):
                summary.skipped_count += 1
                job_record.skipped_files += 1
                summary.document_summaries.append(
                    {
                        "filename": filename,
                        "status": "skipped_unchanged",
                        "chunks": existing_doc.chunk_count,
                        "pages": existing_doc.page_count,
                    }
                )
                logger.info(
                    f"  [~] Skipped unchanged document: {filename} (Chunks: {existing_doc.chunk_count})"
                )
                continue

            # Extract document content
            extraction = DocumentExtractor.extract_file(file_path)

            if extraction.status == "scanned_ocr_required":
                # Handle scanned/image PDF without extractable text
                doc = existing_doc or KBDocument(
                    filename=filename,
                    file_path=file_path,
                    file_type=file_ext,
                    file_size_bytes=file_size,
                    checksum=file_checksum,
                )
                doc.file_path = file_path
                doc.file_size_bytes = file_size
                doc.checksum = file_checksum
                doc.page_count = (
                    extraction.total_pages
                    or extraction.metadata.get("page_count", 0)
                )
                doc.chunk_count = 0
                doc.ingestion_status = "scanned_ocr_required"
                doc.error_message = (
                    extraction.error_message
                    or "Document is image-based. Text layer not present; requires OCR."
                )
                doc.category = category
                doc.doc_metadata = extraction.metadata

                if not existing_doc:
                    self.db.add(doc)
                self.db.flush()

                # Clean any old chunks if previously indexed
                self.db.query(KBChunk).filter(
                    KBChunk.document_id == doc.id
                ).delete()
                self.db.commit()

                summary.scanned_count += 1
                summary.document_summaries.append(
                    {
                        "filename": filename,
                        "status": "scanned_ocr_required",
                        "pages": doc.page_count,
                        "chunks": 0,
                        "note": "Scanned document; OCR required",
                    }
                )
                logger.warning(
                    f"  [!] Scanned document detected (OCR Required): {filename} ({doc.page_count} pages)"
                )
                continue

            elif extraction.status == "unsupported" or extraction.status == "error":
                summary.failed_count += 1
                job_record.failed_files += 1
                summary.document_summaries.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "error": extraction.error_message,
                    }
                )
                logger.error(
                    f"  [-] Failed to process {filename}: {extraction.error_message}"
                )
                continue

            # Success: Chunk and index text
            chunks = self.chunker.chunk_pages(extraction.pages)

            doc = existing_doc or KBDocument(
                filename=filename,
                file_path=file_path,
                file_type=file_ext,
                file_size_bytes=file_size,
                checksum=file_checksum,
            )
            doc.file_path = file_path
            doc.file_size_bytes = file_size
            doc.checksum = file_checksum
            doc.page_count = extraction.total_pages
            doc.chunk_count = len(chunks)
            doc.ingestion_status = "indexed"
            doc.error_message = None
            doc.category = category
            doc.doc_metadata = {
                "total_characters": extraction.total_characters,
                "sections": len(extraction.pages),
            }

            if not existing_doc:
                self.db.add(doc)
            self.db.flush()

            # Remove old chunks if updating an existing document
            self.db.query(KBChunk).filter(
                KBChunk.document_id == doc.id
            ).delete()

            # Insert new chunks
            for chk in chunks:
                chunk_record = KBChunk(
                    document_id=doc.id,
                    chunk_index=chk.chunk_index,
                    page_number=chk.page_number,
                    section_heading=chk.section_heading,
                    content=chk.content,
                    token_count=chk.token_count,
                    checksum=chk.checksum,
                )
                self.db.add(chunk_record)

            self.db.commit()

            summary.indexed_count += 1
            job_record.processed_files += 1
            summary.total_chunks_created += len(chunks)
            summary.document_summaries.append(
                {
                    "filename": filename,
                    "status": "indexed",
                    "pages": doc.page_count,
                    "chunks": len(chunks),
                    "category": category,
                }
            )
            logger.info(
                f"  [+] Indexed {filename} ({doc.page_count} pages -> {len(chunks)} chunks)"
            )

        job_record.status = "completed"
        job_record.completed_at = datetime.now(timezone.utc)
        self.db.commit()

        logger.info(
            f"[KB Ingestion Complete] Indexed: {summary.indexed_count}, Skipped: {summary.skipped_count}, "
            f"Scanned (OCR Req): {summary.scanned_count}, Total Chunks: {summary.total_chunks_created}"
        )
        return summary

    def _compute_file_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file for change detection."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _infer_category(self, filename: str) -> str:
        """Infer academic category from filename."""
        name_lower = filename.lower()
        if "syllabus" in name_lower:
            return "mca_syllabus"
        elif "question" in name_lower or "bank" in name_lower:
            return "question_bank"
        elif "calendar" in name_lower:
            return "academic_calendar"
        elif "notes" in name_lower or "unit" in name_lower:
            return "academic_notes"
        elif "scheme" in name_lower:
            return "curriculum_scheme"
        return "academic_courseware"
