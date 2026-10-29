"""Contextual & Grounded Answer Builder for CampusIQ Chatbot.

Transforms raw retrieved document chunks, structured database records, and question
analysis into well-formatted, detailed, and source-grounded markdown responses.
"""

import re
from typing import Any, Dict, List, Optional, Set

from app.chatbot.intent_classifier import QuestionAnalysis


class AnswerBuilder:
    """Constructs structured, readable, and factually grounded responses."""

    @classmethod
    def format_sources(cls, sources: List[str]) -> str:
        """Format clean, deduplicated source citation pills."""
        if not sources:
            return ""
        clean_sources = []
        for s in sources:
            s_clean = s.strip()
            if s_clean and s_clean not in clean_sources:
                clean_sources.append(s_clean)

        if not clean_sources:
            return ""

        formatted_list = [f"• `{src}`" for src in clean_sources[:4]]
        return "\n\n**Sources & Institutional Citations:**\n" + "\n".join(formatted_list)

    @classmethod
    def build_concept_answer(
        cls, analysis: QuestionAnalysis, chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build detailed, academic explanation with headings, principles, and examples."""
        if not chunks:
            return {
                "text": (
                    f"I searched the indexed course notes for **{analysis.raw_query}**, "
                    f"but could not find a sufficiently authoritative passage in the current repository. "
                    f"Please verify the subject terminology or refer to the recommended textbook."
                ),
                "sources": [],
                "suggestions": ["MCA Syllabus", "DBMS Notes", "DSA Notes", "Operating Systems"],
            }

        subject_title = (analysis.subject_focus or "Computer Science").upper()
        top_chunk = chunks[0]
        heading = top_chunk.get("section_heading") or analysis.raw_query.title()

        # Clean passages
        passages: List[str] = []
        sources: List[str] = []

        for c in chunks[:3]:
            content = c["content"].strip()
            if c["citation"] not in sources:
                sources.append(c["citation"])
            passages.append(content)

        primary_text = passages[0]

        # Extract definition sentence
        definition_match = re.search(r"([^.\n]+(?:is defined as|refers to|is a|is an)[^.\n]+\.)", primary_text, re.IGNORECASE)
        definition_lead = f"> **Key Definition:** {definition_match.group(1).strip()}\n\n" if definition_match else ""

        body_text = "\n\n".join(passages[:2])

        # Assemble rich structured response
        response_md = (
            f"## 📘 {heading} ({subject_title})\n\n"
            f"{definition_lead}"
            f"{body_text}\n\n"
            f"---\n"
            f"*Extracted from JDCOEM Department of MCA verified courseware.*"
            f"{cls.format_sources(sources)}"
        )

        suggestions = [
            f"{subject_title} Question Bank",
            f"MCA Sem 1 Syllabus",
            f"MCA Sem 2 Syllabus",
            "Prof. Rohan Kokate (HOD MCA)",
        ]

        return {
            "text": response_md,
            "sources": sources,
            "suggestions": suggestions,
        }

    @classmethod
    def build_syllabus_answer(
        cls, analysis: QuestionAnalysis, chunks: List[Dict[str, Any]], semester: Optional[int]
    ) -> Dict[str, Any]:
        """Build structured curriculum and course scheme presentation."""
        sem_num = semester or analysis.semester_focus or 1
        sources: List[str] = []
        passages: List[str] = []

        for c in chunks:
            if c["citation"] not in sources:
                sources.append(c["citation"])
            passages.append(c["content"])

        combined_content = "\n\n".join(passages[:3]) if passages else "Syllabus details currently being loaded."

        response_md = (
            f"## 🎓 MCA Semester {sem_num} Academic Scheme & Syllabus\n\n"
            f"**Autonomous Curriculum (DBATU Affiliated | DTE Code: 04138)**\n\n"
            f"{combined_content}\n\n"
            f"### 📋 General Assessment Policy:\n"
            f"- **Continuous Assessment (CA):** 40 Marks (Quizzes, Class Tests, Assignments, Active Lab Performance)\n"
            f"- **Mid-Semester Examination (MSE):** 20 Marks\n"
            f"- **End-Semester Examination (ESE):** 60 Marks (Autonomous Question Paper Pattern)\n"
            f"- **Total Passing Requirement:** Minimum 40% aggregate in CA + MSE + ESE as per Autonomous Regulations.\n"
            f"{cls.format_sources(sources)}"
        )

        suggestions = [
            f"MCA Sem {1 if sem_num == 2 else 2} Syllabus",
            "MCA Course Fees",
            "Prof. Rohan Kokate (HOD MCA)",
            "MCA Project & TBI Incubation",
        ]

        return {
            "text": response_md,
            "sources": sources,
            "suggestions": suggestions,
        }

    @classmethod
    def build_question_bank_answer(
        cls, analysis: QuestionAnalysis, chunks: List[Dict[str, Any]], subject: Optional[str]
    ) -> Dict[str, Any]:
        """Build categorized list of exam and viva preparation questions."""
        subj_name = (subject or analysis.subject_focus or "Academic").upper()
        sources: List[str] = []
        extracted_questions: List[str] = []

        for c in chunks:
            if c["citation"] not in sources:
                sources.append(c["citation"])
            # Split lines and identify questions
            for line in c["content"].split("\n"):
                line_s = line.strip()
                if (
                    "?" in line_s
                    or re.match(r"^(Q\d+|Unit\s*\d+|[0-9]+\.|\([a-z]\))\s+", line_s, re.I)
                    or any(k in line_s.lower() for k in ["explain", "define", "differentiate", "describe", "write a"])
                ):
                    if len(line_s) > 15 and line_s not in extracted_questions:
                        extracted_questions.append(line_s)

        if not extracted_questions and chunks:
            # Fall back to using content paragraphs
            extracted_questions = [c["content"][:300] for c in chunks[:3]]

        q_list_md = "\n".join([f"- {q}" for q in extracted_questions[:8]])

        response_md = (
            f"## 📝 Important Exam & Question Bank: {subj_name}\n\n"
            f"The following questions have been curated from official JDCOEM MCA course question banks:\n\n"
            f"{q_list_md}\n\n"
            f"💡 *Tip: For full 10-mark answers, include block diagrams, syntax examples, and real-world system applications.*"
            f"{cls.format_sources(sources)}"
        )

        suggestions = [
            f"{subj_name} Notes & Concepts",
            "MCA Sem 1 Syllabus",
            "MCA Sem 2 Syllabus",
            "Attendance Policy",
        ]

        return {
            "text": response_md,
            "sources": sources,
            "suggestions": suggestions,
        }

    @classmethod
    def build_comparison_answer(
        cls, analysis: QuestionAnalysis, chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build structured comparative explanation between two concepts."""
        sources: List[str] = []
        for c in chunks:
            if c["citation"] not in sources:
                sources.append(c["citation"])

        content_body = "\n\n".join([c["content"] for c in chunks[:3]]) if chunks else ""

        response_md = (
            f"## ⚖️ Technical Comparison: {analysis.raw_query.title()}\n\n"
            f"{content_body}\n\n"
            f"### 📊 Key Distinctions Summary:\n"
            f"- Refer to the verified notes for formal mathematical and architectural differences.\n"
            f"- Ensure both definition and practical applications are covered in university exam papers.\n"
            f"{cls.format_sources(sources)}"
        )

        return {
            "text": response_md,
            "sources": sources,
            "suggestions": ["MCA Syllabus", "Question Bank", "Prof. Rohan Kokate", "TBI Incubation"],
        }

    @classmethod
    def build_multipart_answer(
        cls, sub_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Combine multiple sub-answers with distinct numbered sections."""
        combined_text_parts: List[str] = [
            "### 📌 Multi-Part Inquiry Response\n\n"
            "Here is the breakdown for each part of your question:\n"
        ]
        all_sources: List[str] = []
        all_suggestions: List[str] = []

        for idx, sub in enumerate(sub_answers, start=1):
            q_title = sub.get("query_title", f"Part {idx}")
            msg = sub.get("text", "")
            combined_text_parts.append(f"#### Part {idx}: {q_title}\n{msg}\n")
            for s in sub.get("sources", []):
                if s not in all_sources:
                    all_sources.append(s)
            for sug in sub.get("suggestions", []):
                if sug not in all_suggestions:
                    all_suggestions.append(sug)

        return {
            "text": "\n\n".join(combined_text_parts),
            "sources": all_sources,
            "suggestions": all_suggestions[:4],
        }
