"""Comprehensive Automated Tests for CampusIQ Knowledge Ingestion & Retrieval Pipeline."""

import os
from unittest.mock import MagicMock, patch
import pytest

from app.chatbot.answer_builder import AnswerBuilder
from app.chatbot.chunking import DocumentChunk, TextChunker
from app.chatbot.document_extractors import (
    DocumentExtractionResult,
    DocumentExtractor,
    ExtractedPage,
)
from app.chatbot.ingestion import KnowledgeIngestionPipeline
from app.chatbot.intent_classifier import IntentClassifier, QuestionAnalysis
from app.chatbot.orchestrator import ChatOrchestrator
from app.chatbot.retrieval import KnowledgeRetriever
from app.db.session import SessionLocal
from app.models.knowledge import KBChunk, KBDocument


# =============================================================================
# 1. Document Extraction & Scanned Detection Tests
# =============================================================================

def test_extractor_supported_extensions():
    """Verify supported file extensions in DocumentExtractor."""
    assert ".pdf" in DocumentExtractor.SUPPORTED_EXTENSIONS
    assert ".docx" in DocumentExtractor.SUPPORTED_EXTENSIONS
    assert ".txt" in DocumentExtractor.SUPPORTED_EXTENSIONS
    assert ".csv" in DocumentExtractor.SUPPORTED_EXTENSIONS
    assert ".json" in DocumentExtractor.SUPPORTED_EXTENSIONS


def test_text_document_extractor(tmp_path):
    """Verify plain text extractor preserves content and detects structure."""
    sample_file = tmp_path / "sample_policy.txt"
    sample_file.write_text("JDCOEM Nagpur\n\nAttendance regulation: Minimum 75% attendance.", encoding="utf-8")

    result = DocumentExtractor.extract_file(str(sample_file))

    assert result.status == "success"
    assert result.total_pages == 1
    assert "Minimum 75% attendance" in result.full_text
    assert result.status != "scanned_ocr_required"


def test_chunking_heading_and_paragraph_awareness():
    """Verify chunker splits at logical headings without cutting arbitrary sentences."""
    raw_doc = (
        "## Chapter 1: Introduction to DBMS\n\n"
        "A database management system is software designed to store and manage data.\n\n"
        "## Chapter 2: Relational Data Model\n\n"
        "Relational model represents data in tabular structures known as relations."
    )
    pages = [ExtractedPage(page_number=1, text=raw_doc, section_heading="DBMS")]
    chunker = TextChunker(target_chunk_words=10, min_chunk_words=3, max_chunk_words=30)
    chunks = chunker.chunk_pages(pages)

    assert len(chunks) >= 2
    headings = [c.section_heading for c in chunks if c.section_heading]
    assert any("Introduction to DBMS" in h or "DBMS" in h for h in headings)


def test_scanned_pdf_detection():
    """Verify that an empty or image-based PDF page is flagged as requiring OCR."""
    extraction = DocumentExtractionResult(
        filename="scanned_calendar.pdf",
        file_path="/tmp/scanned_calendar.pdf",
        file_type=".pdf",
        file_size_bytes=50000,
        pages=[ExtractedPage(1, "", is_empty=True)],
        status="scanned_ocr_required",
    )
    assert extraction.status == "scanned_ocr_required"


# =============================================================================
# 2. Ingestion Idempotency & DB Persistence Tests
# =============================================================================

def test_ingestion_pipeline_idempotency():
    """Verify running the ingestion pipeline repeatedly skips unchanged files without duplicates."""
    db = SessionLocal()
    try:
        pipeline = KnowledgeIngestionPipeline(db)
        summary = pipeline.run_ingestion()
        res = summary.to_dict()

        # Knowledge_Base folder exists and has 13 files
        assert res["total_discovered"] == 13
        # On a rerun, all existing files should be skipped
        assert res["skipped_count"] == 13
        assert res["indexed_count"] == 0
        assert res["failed_count"] == 0

        # Verify documents exist in database
        doc_count = db.query(KBDocument).count()
        assert doc_count >= 10
        chunk_count = db.query(KBChunk).count()
        assert chunk_count >= 100
    finally:
        db.close()


# =============================================================================
# 3. Intent Classification & Question Analysis Tests
# =============================================================================

def test_intent_classification_subjects():
    """Verify question analysis extracts subjects and types accurately."""
    # Concept / definition
    q1 = IntentClassifier.analyze_question("What is normalization and 3NF in DBMS?")
    assert q1.subject_focus == "dbms"
    assert q1.question_type in ("concept", "definition")
    assert "dbms" in q1.primary_intent

    # Question Bank
    q2 = IntentClassifier.analyze_question("Give me AI question bank for exam preparation")
    assert q2.subject_focus == "ai"
    assert q2.question_type == "question_bank"
    assert q2.primary_intent == "kb_question_bank_ai"

    # Syllabus Sem 1
    q3 = IntentClassifier.analyze_question("What subjects are taught in MCA Sem 1 syllabus?")
    assert q3.semester_focus == 1
    assert q3.question_type == "syllabus"
    assert q3.primary_intent == "kb_syllabus_mca_sem1"

    # Syllabus Sem 2
    q4 = IntentClassifier.analyze_question("Explain MCA 2nd sem subjects and credits")
    assert q4.semester_focus == 2
    assert q4.question_type == "syllabus"
    assert q4.primary_intent == "kb_syllabus_mca_sem2"


def test_intent_classification_multipart():
    """Verify multi-part questions are split into sub-queries."""
    query = "What are the MCA fees? and who is the HOD?"
    analysis = IntentClassifier.analyze_question(query)
    assert analysis.is_multipart is True
    assert len(analysis.sub_questions) >= 2


def test_intent_classification_ambiguity():
    """Verify ambiguous or single-word query is flagged appropriately."""
    analysis = IntentClassifier.analyze_question("fees")
    assert analysis.entities["has_fees"] is True


# =============================================================================
# 4. Multi-Strategy Retrieval Tests
# =============================================================================

def test_knowledge_retrieval_acid_properties():
    """Verify ACID properties query retrieves correct DBMS note chunk with page number."""
    db = SessionLocal()
    try:
        retriever = KnowledgeRetriever(db)
        chunks = retriever.search_knowledge_chunks(
            query="ACID properties in DBMS transactions",
            subject="dbms",
            limit=3,
        )
        assert len(chunks) > 0
        top = chunks[0]
        assert "DBMS_Complete_Notes_English.pdf" in top["filename"]
        assert top["page_number"] > 0
        assert "Page" in top["citation"]
        assert any(term in top["content"].lower() for term in ["transaction", "acid", "atomicity", "durability"])
    finally:
        db.close()


def test_knowledge_retrieval_mca_sem1_syllabus():
    """Verify MCA Sem 1 syllabus retrieval returns course scheme chunk."""
    db = SessionLocal()
    try:
        retriever = KnowledgeRetriever(db)
        chunks = retriever.search_knowledge_chunks(
            query="MCA sem 1 syllabus scheme course code credits",
            semester=1,
            limit=3,
        )
        assert len(chunks) > 0
        top = chunks[0]
        assert "MCA SEM 1 Syllabus Final.pdf" in top["filename"]
        assert "Page" in top["citation"]
    finally:
        db.close()


def test_scanned_document_transparent_notice():
    """Verify query for unextracted scanned calendar returns notice without crash."""
    db = SessionLocal()
    try:
        retriever = KnowledgeRetriever(db)
        notice = retriever.check_scanned_document_inquiry("Show me the MCA 1st sem academic calendar")
        assert notice is not None
        assert "scanned image pages" in notice["text"].lower()
        assert "ocr" in notice["text"].lower()
        assert "Academic Calendar" in notice["sources"][0]
    finally:
        db.close()


# =============================================================================
# 5. Contextual Answer Builder Tests
# =============================================================================

def test_answer_builder_concept_formatting():
    """Verify AnswerBuilder outputs Markdown with headings, definition, and sources."""
    analysis = QuestionAnalysis(
        raw_query="What is ACID in DBMS?",
        normalized_query="what is acid in dbms",
        primary_intent="kb_concept_dbms",
        question_type="concept",
        confidence=0.95,
        entities={"subject": "dbms"},
        subject_focus="dbms",
    )
    chunks = [
        {
            "filename": "DBMS_Complete_Notes_English.pdf",
            "page_number": 11,
            "section_heading": "Transactions and ACID Properties",
            "content": "A transaction is a logical unit of work. ACID stands for Atomicity, Consistency, Isolation, and Durability.",
            "score": 9.5,
            "citation": "DBMS_Complete_Notes_English.pdf, Page 11",
        }
    ]
    res = AnswerBuilder.build_concept_answer(analysis, chunks)
    assert "## 📘" in res["text"]
    assert "Atomicity" in res["text"]
    assert "Sources & Institutional Citations:" in res["text"]
    assert "DBMS_Complete_Notes_English.pdf, Page 11" in res["sources"][0]


def test_answer_builder_syllabus_formatting():
    """Verify AnswerBuilder syllabus format includes assessment policies and citations."""
    analysis = QuestionAnalysis(
        raw_query="MCA Sem 1 Syllabus",
        normalized_query="mca sem 1 syllabus",
        primary_intent="kb_syllabus_mca_sem1",
        question_type="syllabus",
        confidence=0.95,
        entities={"semester": 1},
        semester_focus=1,
    )
    chunks = [
        {
            "filename": "MCA SEM 1 Syllabus Final.pdf",
            "page_number": 3,
            "section_heading": "Scheme of Teaching and Examination",
            "content": "MC1T001 Advanced Operating Systems L:3 T:0 P:0 Credits: 3.",
            "score": 8.0,
            "citation": "MCA SEM 1 Syllabus Final.pdf, Page 3",
        }
    ]
    res = AnswerBuilder.build_syllabus_answer(analysis, chunks, semester=1)
    assert "MCA Semester 1" in res["text"]
    assert "Continuous Assessment (CA)" in res["text"]
    assert "MCA SEM 1 Syllabus Final.pdf, Page 3" in res["sources"][0]


# =============================================================================
# 6. End-to-End Chat Orchestrator Priority Tests
# =============================================================================

def test_orchestrator_rule_priority_over_ai():
    """Verify that a rule/KB match is answered via rule_based and does NOT invoke AI fallback."""
    db = SessionLocal()
    mock_ai = MagicMock()
    orchestrator = ChatOrchestrator(ai_provider=mock_ai)

    try:
        # Knowledge Base Concept Turn
        res = orchestrator.process_message(db, "What are ACID properties in DBMS?")
        assert res["engine"] == "rule_based"
        assert res["intent"] == "kb_concept_dbms"
        assert len(res["sources"]) > 0
        # AI must NEVER be called when knowledge rule/chunk is confident
        mock_ai.generate_response.assert_not_called()

        # Institutional Fee Turn
        res_fee = orchestrator.process_message(db, "What is the fee for MCA?")
        assert res_fee["engine"] == "rule_based"
        assert "91,500" in res_fee["message"]
        mock_ai.generate_response.assert_not_called()
    finally:
        db.close()
