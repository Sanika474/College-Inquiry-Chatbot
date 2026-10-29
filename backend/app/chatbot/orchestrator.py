"""Chat Orchestrator for CampusIQ.

Coordinates rule-based classification, database knowledge retrieval, knowledge-base
chunk search, contextual answer building, conversation persistence, and grounded AI fallback.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.chatbot.ai_provider import AIProvider
from app.chatbot.answer_builder import AnswerBuilder
from app.chatbot.intent_catalog import IntentCategory
from app.chatbot.intent_classifier import IntentClassifier, QuestionAnalysis
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
        history = [{"sender": m.sender, "content": m.content} for m in past_msgs[-6:]]

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

        # 3. Check for queries regarding unextracted/scanned documents
        scanned_notice = retriever.check_scanned_document_inquiry(user_message)
        if scanned_notice:
            answer_text = scanned_notice["text"]
            sources = scanned_notice["sources"]
            suggestions = scanned_notice.get("suggestions", [])
            final_intent = "kb_scanned_document_notice"
            final_category = "knowledge_base"

        # 4. Perform Question Structural Analysis
        analysis: QuestionAnalysis = self.intent_classifier.analyze_question(user_message, history)

        # 5. Handle Multi-Part Queries
        if not answer_text and analysis.is_multipart and len(analysis.sub_questions) >= 2:
            sub_answers: List[Dict[str, Any]] = []
            for sub_q in analysis.sub_questions:
                sub_match = self.rule_engine.classify(sub_q)
                if sub_match.intent_id != "unknown":
                    sub_data = self._execute_institutional_rule(retriever, sub_match)
                    sub_answers.append({
                        "query_title": sub_q,
                        "text": sub_data.get("text", ""),
                        "sources": sub_data.get("sources", []),
                        "suggestions": sub_data.get("suggestions", []),
                    })
                else:
                    # Try chunk retrieval for sub-question
                    chunks = retriever.search_knowledge_chunks(sub_q, limit=2)
                    if chunks:
                        sub_answers.append({
                            "query_title": sub_q,
                            "text": chunks[0]["content"],
                            "sources": [chunks[0]["citation"]],
                            "suggestions": [],
                        })
                    else:
                        sub_answers.append({
                            "query_title": sub_q,
                            "text": "Information for this specific part is not present in the institutional documents.",
                            "sources": [],
                            "suggestions": [],
                        })

            multipart_res = self.answer_builder.build_multipart_answer(sub_answers)
            answer_text = multipart_res["text"]
            sources = multipart_res["sources"]
            suggestions = multipart_res["suggestions"]
            final_intent = "multipart_inquiry"
            final_category = "multipart"
            processing_engine = "rule_based"

        # 6. Standard Rule Engine Matching (Greetings, Clarification, Institutional Rules)
        match: RuleMatchResult = self.rule_engine.classify(user_message)

        if not answer_text:
            if match.is_ambiguous and match.clarification_prompt:
                answer_text = match.clarification_prompt
                processing_engine = "clarification"
                sources = ["CampusIQ Query Clarifier"]
                suggestions = match.suggestions
                final_intent = match.intent_id
                final_category = match.category
                final_confidence = match.confidence

            elif match.intent_id == "greeting":
                answer_text = (
                    "Hello! 👋 Welcome to **CampusIQ — Intelligent College Companion** for "
                    "**JD College of Engineering & Management (JDCOEM), Nagpur**.\n\n"
                    "I am your digital companion for the **Master of Computer Applications (MCA)** department "
                    "and broader autonomous engineering programs.\n\n"
                    "How can I assist you today? You can ask me about MCA fees, syllabus, eligibility, "
                    "Prof. Rohan Kokate, TBI incubation, or campus placements!"
                )
                sources = ["CampusIQ Assistant"]
                suggestions = match.suggestions
                final_intent = "greeting"
                final_category = IntentCategory.GREETING.value

            elif match.intent_id == "farewell":
                answer_text = (
                    "Thank you for connecting with CampusIQ! If you have any further questions regarding "
                    "MCA admissions, fees, or JDCOEM campus life, feel free to ask anytime. Have a successful day! 😊"
                )
                sources = ["CampusIQ Assistant"]
                final_intent = "farewell"
                final_category = IntentCategory.FAREWELL.value

            elif match.intent_id == "help_capabilities":
                answer_text = (
                    "**CampusIQ — JDCOEM Academic Services & Capabilities:**\n\n"
                    "As the authoritative AI and rule-based assistant for JD College of Engineering & Management, I provide factual data on:\n"
                    "- **MCA Department:** Curriculum, 2-year duration, intake (120 seats), and faculty roster\n"
                    "- **Tuition Fees:** FRA-approved multi-year fee schedules (MCA: ₹91,500/year, B.Tech: ₹1,00,000/year)\n"
                    "- **Admissions & DTE CAP:** Eligibility criteria, MAH-MCA-CET cutoffs, and DTE Choice Code 04138\n"
                    "- **Department Leadership:** Principal Dr. Shrikant V. Sonekar, HOD Prof. Rohan Kokate, Prof. Chetan Padole\n"
                    "- **Incubation & Innovation:** Technology Business Incubator (TBI) for student software startups\n"
                    "- **Campus Facilities:** Central Digital Library, AI/GPU Labs, Hostels, and Citywide Bus Transport\n"
                    "- **Campus Regulations:** Mandatory 75% attendance rule and anti-ragging policies"
                )
                sources = ["CampusIQ Capability Matrix"]
                suggestions = match.suggestions
                final_intent = "help_capabilities"
                final_category = IntentCategory.HELP.value

            elif match.intent_id != "unknown" and analysis.question_type not in (
                "syllabus",
                "question_bank",
                "concept",
                "comparison",
            ):
                # Standard Institutional Database Lookup
                inst_data = self._execute_institutional_rule(retriever, match)
                answer_text = inst_data.get("text", "")
                sources = inst_data.get("sources", ["College Official Records"])
                suggestions = inst_data.get("suggestions", match.suggestions)
                final_intent = match.intent_id
                final_category = match.category
                final_confidence = match.confidence

        # 7. Knowledge Base Document Chunk Search (Syllabus, Notes, Question Banks, Concepts)
        if not answer_text or (match.intent_id == "unknown" and not answer_text):
            is_academic_query = (
                analysis.subject_focus is not None
                or analysis.semester_focus is not None
                or analysis.question_type in ("syllabus", "question_bank", "concept", "comparison")
                or analysis.primary_intent.startswith("kb_")
            )

            if is_academic_query:
                if analysis.question_type == "syllabus" or analysis.primary_intent.startswith("kb_syllabus"):
                    chunks = retriever.search_knowledge_chunks(
                        user_message,
                        semester=analysis.semester_focus,
                        subject=analysis.subject_focus,
                        limit=4,
                    )
                    if chunks:
                        kb_res = self.answer_builder.build_syllabus_answer(
                            analysis, chunks, analysis.semester_focus
                        )
                        answer_text = kb_res["text"]
                        sources = kb_res["sources"]
                        suggestions = kb_res["suggestions"]
                        final_intent = analysis.primary_intent
                        final_category = "syllabus"
                        processing_engine = "rule_based"

                elif analysis.question_type == "question_bank" or analysis.primary_intent.startswith("kb_question_bank"):
                    chunks = retriever.search_knowledge_chunks(
                        user_message,
                        subject=analysis.subject_focus,
                        limit=6,
                    )
                    if chunks:
                        kb_res = self.answer_builder.build_question_bank_answer(
                            analysis, chunks, analysis.subject_focus
                        )
                        answer_text = kb_res["text"]
                        sources = kb_res["sources"]
                        suggestions = kb_res["suggestions"]
                        final_intent = analysis.primary_intent
                        final_category = "question_bank"
                        processing_engine = "rule_based"

                else:
                    # Concept / Definition / Comparison from Notes
                    chunks = retriever.search_knowledge_chunks(
                        user_message,
                        subject=analysis.subject_focus,
                        limit=4,
                    )
                    if chunks and (chunks[0]["score"] >= 1.2 or analysis.subject_focus):
                        if analysis.question_type == "comparison":
                            kb_res = self.answer_builder.build_comparison_answer(analysis, chunks)
                        else:
                            kb_res = self.answer_builder.build_concept_answer(analysis, chunks)

                        answer_text = kb_res["text"]
                        sources = kb_res["sources"]
                        suggestions = kb_res["suggestions"]
                        final_intent = analysis.primary_intent
                        final_category = "concept"
                        processing_engine = "rule_based"

        # 8. Out-of-Domain AI Fallback or Verified Rule-Based Fallback
        if not answer_text:
            if self.ai_provider.is_available():
                ai_res = self.ai_provider.generate_response(user_message)
                if ai_res and ai_res.get("text"):
                    answer_text = ai_res["text"]
                    processing_engine = "ai_fallback"
                    sources = [ai_res.get("source", "CampusIQ Grounded AI Fallback")]
                    suggestions = [
                        "MCA Course Details",
                        "Prof. Rohan Kokate (HOD MCA)",
                        "TBI Incubation",
                        "Contact JDCOEM",
                    ]
                    final_intent = "ai_fallback"
                    final_category = "ai"

            if not answer_text:
                answer_text = (
                    "I couldn't locate specific information for that in the JDCOEM official catalog. "
                    "Here are some popular topics you can ask me about:\n\n"
                    "- MCA course fee schedule (FRA approved: ₹91,500/year)\n"
                    "- MCA admission eligibility & MAH-MCA-CET CAP rounds (DTE Code: 04138)\n"
                    "- MCA HOD Prof. Rohan Kokate & Project Coordinator Prof. Chetan Padole\n"
                    "- Technology Business Incubator (TBI) & student startup support\n"
                    "- Campus placements (TCS, Infosys, Wipro, Capgemini) & bus transport routes"
                )
                processing_engine = "rule_based"
                sources = ["JDCOEM Information Helpdesk"]
                final_intent = "unknown"
                final_category = IntentCategory.UNKNOWN.value
                suggestions = [
                    "MCA Course Details",
                    "MCA Fees (FRA Sanctioned)",
                    "Who is the Principal?",
                    "TBI Startup Incubation",
                ]

        # 9. Record bot response in database
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

        return {
            "conversation_id": conversation.id,
            "message": answer_text,
            "intent": final_intent,
            "category": final_category,
            "engine": processing_engine,
            "confidence": final_confidence,
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
