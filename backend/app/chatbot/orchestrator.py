"""Chat Orchestrator for CampusIQ.

Coordinates Question Understanding, Knowledge Graph retrieval, intent-specific answer
generation, document link management, conversation history persistence, and grounded AI fallback.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.chatbot.ai_provider import AIProvider
from app.chatbot.answer_builder import AnswerBuilder
from app.chatbot.intent_catalog import IntentCategory
from app.chatbot.intent_classifier import IntentClassifier, IntentString, QuestionAnalysis, StandardIntent
from app.chatbot.knowledge_graph import knowledge_graph
from app.chatbot.retrieval import KnowledgeRetriever
from app.chatbot.rule_engine import RuleEngine, RuleMatchResult
from app.models.conversation import Conversation, Message


class ChatOrchestrator:
    """Manages chat turn lifecycle, intent execution, knowledge extraction, and persistence."""

    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        ai_provider: Optional[AIProvider] = None,
    ):
        self.rule_engine = rule_engine or RuleEngine()
        self.ai_provider = ai_provider or AIProvider()
        self.intent_classifier = IntentClassifier
        self.answer_builder = AnswerBuilder

    def process_message(
        self,
        db: Session,
        user_message: str,
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Process incoming user message and return structured, grounded response."""
        # 1. Resolve or create Conversation session
        conversation = None
        if conversation_id:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation and user_id and not conversation.user_id:
                conversation.user_id = user_id

        if not conversation:
            clean_title = (
                (user_message.strip()[:35] + "...")
                if len(user_message.strip()) > 35
                else (user_message.strip() or "New Inquiry")
            )
            conversation = Conversation(user_id=user_id, title=clean_title)
            db.add(conversation)
            db.flush()

        # Retrieve recent conversation turns for context & follow-ups
        past_msgs = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        history = [{"sender": m.sender, "content": m.content} for m in past_msgs[-8:]]

        # 2. Record incoming user message
        user_msg = Message(
            conversation_id=conversation.id,
            sender="user",
            content=user_message,
            processing_engine="user_input",
            confidence_score=1.0,
        )
        db.add(user_msg)
        db.flush()

        retriever = KnowledgeRetriever(db)
        answer_text = ""
        processing_engine = "rule_based"
        sources: List[str] = []
        suggestions: List[str] = []
        final_intent = "unknown"
        final_confidence = 1.0
        final_category = IntentCategory.UNKNOWN.value
        response_format = "text"
        structured_items: List[Dict[str, Any]] = []
        document_links: List[Dict[str, Any]] = []

        # 3. Check legacy ambiguous queries (e.g. single word "fees")
        legacy_match: RuleMatchResult = self.rule_engine.classify(user_message)
        if legacy_match.is_ambiguous and legacy_match.clarification_prompt:
            answer_text = legacy_match.clarification_prompt
            processing_engine = "clarification"
            sources = ["CampusIQ Query Clarifier"]
            suggestions = legacy_match.suggestions
            final_intent = legacy_match.intent_id
            final_category = legacy_match.category
            final_confidence = legacy_match.confidence
            response_format = "clarification"

        # 4. Perform Question Understanding & Entity Extraction
        if not answer_text:
            analysis: QuestionAnalysis = self.intent_classifier.analyze_question(user_message, history)
            intent = analysis.primary_intent

            # Intent 1: GREETING
            if intent == StandardIntent.GREETING.value:
                answer_text = (
                    "Hello! 👋 Welcome to **CampusIQ — Intelligent College Companion** for "
                    "**JD College of Engineering & Management (JDCOEM), Nagpur**.\n\n"
                    "I am your digital companion for the **Master of Computer Applications (MCA)** department "
                    "and broader autonomous engineering programs.\n\n"
                    "How can I assist you today? You can ask me about MCA fees, syllabus, eligibility, "
                    "Prof. Rohan Kokate, TBI incubation, or campus placements!"
                )
                sources = ["CampusIQ Assistant"]
                suggestions = [
                    "MCA Sem 2 Syllabus",
                    "What is the MCA fee?",
                    "Which documents are required for admission?",
                    "Show MCA timetable",
                ]
                final_intent = "greeting"
                final_category = IntentCategory.GREETING.value
                final_confidence = analysis.confidence

            # Intent 2: SYLLABUS_OVERVIEW
            elif intent == StandardIntent.SYLLABUS_OVERVIEW.value:
                sem = analysis.semester_focus or 2
                res = self.answer_builder.build_syllabus_overview(semester=sem)
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                structured_items = res.get("items", [])
                document_links = res.get("links", [])
                final_intent = IntentString("SYLLABUS_OVERVIEW", aliases=[f"kb_syllabus_mca_sem{sem}"])
                final_category = "syllabus"
                final_confidence = 0.95

            # Intent 3: SUBJECT_DETAILS
            elif intent == StandardIntent.SUBJECT_DETAILS.value or (isinstance(intent, str) and intent.startswith("kb_concept_")):
                subj = analysis.subject_focus or "dbms"
                res = self.answer_builder.build_subject_details(subj)
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                structured_items = res.get("items", [])
                document_links = res.get("links", [])
                final_intent = IntentString("SUBJECT_DETAILS", aliases=[f"kb_concept_{subj}"])
                final_category = "subject_details"
                final_confidence = 0.95

            # Intent 4: TIMETABLE
            elif intent == StandardIntent.TIMETABLE.value:
                sem = analysis.semester_focus or 2
                res = self.answer_builder.build_timetable(semester=sem)
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                structured_items = res.get("items", [])
                document_links = res.get("links", [])
                final_intent = "TIMETABLE"
                final_category = "timetable"
                final_confidence = 0.95

            # Intent 5: EXAM_SCHEDULE
            elif intent == StandardIntent.EXAM_SCHEDULE.value:
                res = self.answer_builder.build_exam_schedule(
                    subject_key=analysis.subject_focus,
                    semester=analysis.semester_focus or 2,
                )
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                document_links = res.get("links", [])
                final_intent = "EXAM_SCHEDULE"
                final_category = "examination"
                final_confidence = 0.95

            # Intent 6: COURSE_STRUCTURE
            elif intent == StandardIntent.COURSE_STRUCTURE.value:
                res = self.answer_builder.build_course_structure(analysis.subject_focus)
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                final_intent = "COURSE_STRUCTURE"
                final_category = "course_structure"
                final_confidence = 0.92

            # Intent 7: CREDITS_AND_MARKS
            elif intent == StandardIntent.CREDITS_AND_MARKS.value:
                res = self.answer_builder.build_credits_and_marks(
                    analysis.subject_focus, analysis.semester_focus
                )
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                structured_items = res.get("items", [])
                document_links = res.get("links", [])
                final_intent = "CREDITS_AND_MARKS"
                final_category = "credits_and_marks"
                final_confidence = 0.95

            # Intent 8: FEES
            elif intent == StandardIntent.FEES.value:
                # If specific course is in legacy match, check target
                res = self.answer_builder.build_fees("MCA")
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                structured_items = res.get("items", [])
                final_intent = "fees_mca"
                final_category = IntentCategory.COURSE_FEES.value
                final_confidence = 0.95

            # Intent 9: ADMISSION
            elif intent == StandardIntent.ADMISSION.value:
                res = self.answer_builder.build_admission_process()
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                final_intent = "ADMISSION"
                final_category = IntentCategory.ADMISSION.value
                final_confidence = 0.94

            # Intent 10: FACULTY_DETAILS
            elif intent == StandardIntent.FACULTY_DETAILS.value:
                res = self.answer_builder.build_faculty_info(analysis.entities.get("name"))
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                final_intent = legacy_match.intent_id if "faculty_" in legacy_match.intent_id else "FACULTY_DETAILS"
                final_category = IntentCategory.FACULTY.value
                final_confidence = 0.95

            # Intent 11: DEPARTMENT_INFORMATION
            elif intent == StandardIntent.DEPARTMENT_INFORMATION.value:
                res = self.answer_builder.build_department_info()
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                final_intent = "DEPARTMENT_INFORMATION"
                final_category = IntentCategory.DEPARTMENT.value
                final_confidence = 0.92

            # Intent 12: ELIGIBILITY
            elif intent == StandardIntent.ELIGIBILITY.value:
                res = self.answer_builder.build_eligibility()
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                final_intent = "ELIGIBILITY"
                final_category = IntentCategory.ELIGIBILITY.value
                final_confidence = 0.94

            # Intent 13: DOCUMENTS_REQUIRED
            elif intent == StandardIntent.DOCUMENTS_REQUIRED.value:
                res = self.answer_builder.build_documents_required()
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                final_intent = "DOCUMENTS_REQUIRED"
                final_category = "documents_required"
                final_confidence = 0.95

            # Intent 14: CONTACT_INFORMATION
            elif intent == StandardIntent.CONTACT_INFORMATION.value:
                res = self.answer_builder.build_contact_info()
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                final_intent = "CONTACT_INFORMATION"
                final_category = IntentCategory.CONTACT.value
                final_confidence = 0.95

            # Intent 15: ACADEMIC_CALENDAR
            elif intent == StandardIntent.ACADEMIC_CALENDAR.value:
                res = self.answer_builder.build_academic_calendar()
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                document_links = res.get("links", [])
                final_intent = "ACADEMIC_CALENDAR"
                final_category = "academic_calendar"
                final_confidence = 0.94

            # Intent 16: PRACTICAL_AND_LAB_DETAILS
            elif intent == StandardIntent.PRACTICAL_AND_LAB_DETAILS.value:
                lab_key = analysis.subject_focus or "dbms_lab"
                res = self.answer_builder.build_practical_lab(lab_key)
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                response_format = res["format"]
                structured_items = res.get("items", [])
                document_links = res.get("links", [])
                final_intent = "PRACTICAL_AND_LAB_DETAILS"
                final_category = "practicals"
                final_confidence = 0.94

            # Legacy Rules Fallback: Institutional policy, library, hostel, sports, ragging
            elif legacy_match.intent_id != "unknown":
                inst_data = self._execute_institutional_rule(retriever, legacy_match)
                answer_text = inst_data.get("text", "")
                sources = inst_data.get("sources", ["College Official Records"])
                suggestions = inst_data.get("suggestions", legacy_match.suggestions)
                final_intent = legacy_match.intent_id
                final_category = legacy_match.category
                final_confidence = legacy_match.confidence

        # 5. Out-of-Domain AI Fallback or Zero-Hallucination Fallback
        if not answer_text:
            if self.ai_provider.is_available():
                ai_res = self.ai_provider.generate_response(user_message)
                if ai_res and ai_res.get("text"):
                    answer_text = ai_res["text"]
                    processing_engine = "ai_fallback"
                    sources = [ai_res.get("source", "CampusIQ Grounded AI Fallback")]
                    suggestions = ["MCA Course Details", "MCA Sem 2 Syllabus", "What is the MCA fee?"]
                    final_intent = "ai_fallback"
                    final_category = "ai"

            # Check if query is academic/notes concept
            if not answer_text and analysis.subject_focus:
                chunks = retriever.search_knowledge_chunks(user_message, subject=analysis.subject_focus, limit=2)
                if chunks and chunks[0]["score"] >= 3.0:
                    top = chunks[0]
                    answer_text = (
                        f"## 📘 {top.get('section_heading') or 'Academic Notes'}\n\n"
                        f"{top['content'][:400]}...\n\n"
                        f"*Source: {top['citation']}*"
                    )
                    sources = [top["citation"]]
                    final_intent = IntentString("academic_notes", aliases=[f"kb_concept_{analysis.subject_focus}"])
                    final_category = "notes"

            if not answer_text:
                res = self.answer_builder.build_unknown_response()
                answer_text = res["text"]
                sources = res["sources"]
                suggestions = res["suggestions"]
                final_intent = "unknown"
                final_category = IntentCategory.UNKNOWN.value
                final_confidence = 0.0

        # 6. Record bot response in database
        bot_msg = Message(
            conversation_id=conversation.id,
            sender="bot",
            content=answer_text,
            intent=final_intent,
            processing_engine=processing_engine,
            confidence_score=final_confidence,
            source_reference="; ".join(sources) if sources else None,
        )
        db.add(bot_msg)
        db.commit()

        # Build response payload
        return {
            "conversation_id": conversation.id,
            "message": answer_text,
            "answer": answer_text,
            "intent": final_intent,
            "category": final_category,
            "format": response_format,
            "engine": processing_engine,
            "confidence": final_confidence,
            "items": structured_items,
            "links": document_links,
            "sources": sources,
            "suggestions": suggestions,
            "created_at": bot_msg.created_at,
        }

    def _execute_institutional_rule(
        self, retriever: KnowledgeRetriever, match: RuleMatchResult
    ) -> Dict[str, Any]:
        """Fetch verified data from PostgreSQL institutional tables."""
        cat = match.category
        if cat == IntentCategory.COURSE_FEES.value:
            return retriever.get_course_fees(match.target_entity)
        elif cat == IntentCategory.COURSES.value:
            if match.target_entity:
                return retriever.get_course_detail(match.target_entity)
            return retriever.get_courses_list()
        elif cat == IntentCategory.FACULTY.value:
            return retriever.get_faculty_info(match.target_entity)
        elif cat == IntentCategory.DEPARTMENT.value:
            return retriever.get_departments_list()
        elif cat in (
            IntentCategory.LIBRARY.value,
            IntentCategory.HOSTEL.value,
            IntentCategory.SPORTS.value,
            IntentCategory.FACILITIES.value,
        ):
            return retriever.get_facility_info(match.target_entity)
        elif cat in (IntentCategory.ATTENDANCE.value, IntentCategory.NCC_NSS.value) or "policy" in match.intent_id:
            return retriever.get_knowledge_document(match.intent_id)
        elif cat == IntentCategory.CONTACT.value:
            return retriever.get_contact_info()
        return retriever.get_college_info()
