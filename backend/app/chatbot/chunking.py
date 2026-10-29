"""Chunking strategies for CampusIQ Knowledge Base documents.

Splits extracted pages and sections into semantically meaningful chunks at paragraph,
heading, and table boundaries while preserving source page and heading metadata.
"""

import hashlib
import re
from typing import List, Optional
from app.chatbot.document_extractors import ExtractedPage


class DocumentChunk:
    """Represents a discrete, searchable chunk of a document."""

    def __init__(
        self,
        chunk_index: int,
        content: str,
        page_number: int,
        section_heading: Optional[str] = None,
        token_count: Optional[int] = None,
        checksum: Optional[str] = None,
    ):
        self.chunk_index = chunk_index
        self.content = content.strip()
        self.page_number = page_number
        self.section_heading = section_heading
        self.token_count = token_count or len(self.content.split())
        self.checksum = checksum or hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return f"<DocumentChunk #{self.chunk_index} Page {self.page_number} ({self.token_count} words)>"


class TextChunker:
    """Intelligently chunks extracted document pages into cohesive passages."""

    def __init__(
        self,
        target_chunk_words: int = 220,
        min_chunk_words: int = 35,
        max_chunk_words: int = 400,
        overlap_words: int = 25,
    ):
        self.target_chunk_words = target_chunk_words
        self.min_chunk_words = min_chunk_words
        self.max_chunk_words = max_chunk_words
        self.overlap_words = overlap_words

    def chunk_pages(self, pages: List[ExtractedPage]) -> List[DocumentChunk]:
        """Convert a list of extracted pages into an indexed list of DocumentChunks."""
        chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page in pages:
            if page.is_empty or not page.text:
                continue

            page_chunks = self._chunk_single_page(page, global_chunk_idx)
            chunks.extend(page_chunks)
            global_chunk_idx += len(page_chunks)

        return chunks

    def _chunk_single_page(self, page: ExtractedPage, start_index: int) -> List[DocumentChunk]:
        """Split a single page by headings, double-newlines, and paragraphs."""
        raw_text = page.text
        # Normalize double carriage returns
        raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

        # Split on double newlines or heading indicators
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        if not paragraphs:
            # Fallback to single newline if no double newlines exist
            paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]

        current_heading = page.section_heading
        chunks: List[DocumentChunk] = []
        current_words: List[str] = []
        chunk_counter = start_index

        for para in paragraphs:
            # Detect potential sub-headings inside paragraph
            if self._is_candidate_heading(para):
                current_heading = para[:120].strip()

            para_words = para.split()
            if not para_words:
                continue

            # If adding this paragraph exceeds maximum chunk size, flush current
            if len(current_words) + len(para_words) > self.max_chunk_words and len(current_words) >= self.min_chunk_words:
                content_str = " ".join(current_words)
                chunks.append(
                    DocumentChunk(
                        chunk_index=chunk_counter,
                        content=content_str,
                        page_number=page.page_number,
                        section_heading=current_heading,
                        token_count=len(current_words),
                    )
                )
                chunk_counter += 1

                # Keep overlap words from the end
                if self.overlap_words > 0 and len(current_words) > self.overlap_words:
                    current_words = current_words[-self.overlap_words :]
                else:
                    current_words = []

            current_words.extend(para_words)

            # If current words reached target chunk size, create chunk
            if len(current_words) >= self.target_chunk_words:
                content_str = " ".join(current_words)
                chunks.append(
                    DocumentChunk(
                        chunk_index=chunk_counter,
                        content=content_str,
                        page_number=page.page_number,
                        section_heading=current_heading,
                        token_count=len(current_words),
                    )
                )
                chunk_counter += 1

                # Keep overlap
                if self.overlap_words > 0 and len(current_words) > self.overlap_words:
                    current_words = current_words[-self.overlap_words :]
                else:
                    current_words = []

        # Flush remaining words
        if current_words and len(current_words) >= self.min_chunk_words:
            content_str = " ".join(current_words)
            chunks.append(
                DocumentChunk(
                    chunk_index=chunk_counter,
                    content=content_str,
                    page_number=page.page_number,
                    section_heading=current_heading,
                    token_count=len(current_words),
                )
            )
        elif current_words and chunks:
            # Append trailing short fragment to the previous chunk to avoid losing short trailing requirements
            prev = chunks[-1]
            prev.content = prev.content + "\n" + " ".join(current_words)
            prev.token_count = len(prev.content.split())
            prev.checksum = hashlib.sha256(prev.content.encode("utf-8")).hexdigest()
        elif current_words and not chunks:
            # Single short paragraph on page
            content_str = " ".join(current_words)
            chunks.append(
                DocumentChunk(
                    chunk_index=chunk_counter,
                    content=content_str,
                    page_number=page.page_number,
                    section_heading=current_heading,
                    token_count=len(current_words),
                )
            )

        return chunks

    def _is_candidate_heading(self, text: str) -> bool:
        """Determine if a line resembles a chapter, section, or unit heading."""
        clean = text.strip()
        if len(clean) > 90 or len(clean) < 3:
            return False
        # Heading markers like Unit I, Chapter 1, Section A, Module 3, Course Code
        heading_patterns = [
            r"^(unit|chapter|module|section|part)\s+[0-9ivxabc]+",
            r"^(course|syllabus|subject|code)\s*:",
            r"^[0-9]+\.[0-9]+\s+[A-Z]",
            r"^[A-Z\s]{4,40}$",  # ALL CAPS LINE
        ]
        return any(re.search(pat, clean, re.IGNORECASE) for pat in heading_patterns)
