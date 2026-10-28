"""Chat Orchestrator for CampusIQ.

Coordinates rule-based classification, database knowledge retrieval, conversation
persistence, and optional AI fallback routing.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.chatbot.ai_provider import AIProvider
from app.chatbot.intent_catalog import IntentCategory
from app.chatbot.retrieval import KnowledgeRetriever
from app.chatbot.rule_engine import RuleEngine, RuleMatchResult
from app.models.conversation import Conversation, Message


class ChatOrchestrator:
    """Manages chat turn lifecycle, intent execution, and persistence."""

    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        ai_provider: Optional[AIProvider] = None,
    ):
        self.rule_engine = rule_engine or RuleEngine()
        self.ai_provider = ai_provider or AIProvider()

    def process_message(
        self,
        db: Session,
        user_message: str,
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Process incoming user message and return structured response."""
        # 1. Resolve or create Conversation session
        conversation = None
        if conversation_id:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation and user_id and not conversation.user_id:
                # Associate guest conversation with authenticated user
                conversation.user_id = user_id

        if not conversation:
            clean_title = (user_message.strip()[:35] + "...") if len(user_message.strip()) > 35 else (user_message.strip() or "New Inquiry")
            conversation = Conversation(user_id=user_id, title=clean_title)
            db.add(conversation)
            db.flush()

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

        # 3. Classify with Rule Engine
        match: RuleMatchResult = self.rule_engine.classify(user_message)
        retriever = KnowledgeRetriever(db)

        # 4. Generate response content
        answer_text = ""
        processing_engine = "rule_based"
        sources: List[str] = []
        suggestions = match.suggestions

        if match.is_ambiguous and match.clarification_prompt:
            answer_text = match.clarification_prompt
            processing_engine = "clarification"
            sources = ["CampusIQ Query Clarifier"]

        elif match.intent_id == "unknown":
            # Attempt grounded AI fallback if configured
            ai_res = self.ai_provider.generate_response(user_message)
            if ai_res and ai_res.get("text"):
                answer_text = ai_res["text"]
                processing_engine = "ai_fallback"
                sources = [ai_res.get("source", "CampusIQ Grounded AI Fallback")]
                suggestions = ["MCA Course Details", "Prof. Rohan Kokate (HOD MCA)", "TBI Incubation", "Contact JDCOEM"]
            else:
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

        elif match.intent_id == "greeting":
            answer_text = (
                "Hello! 👋 Welcome to **CampusIQ — Intelligent College Companion** for **JD College of Engineering & Management (JDCOEM), Nagpur**.\n\n"
                "I am your digital companion for the **Master of Computer Applications (MCA)** department and broader autonomous engineering programs.\n\n"
                "How can I assist you today? You can ask me about MCA fees, syllabus, eligibility, Prof. Rohan Kokate, TBI incubation, or campus placements!"
            )
            sources = ["CampusIQ Assistant"]

        elif match.intent_id == "farewell":
            answer_text = (
                "Thank you for connecting with CampusIQ! If you have any further questions regarding MCA admissions, fees, or JDCOEM campus life, feel free to ask anytime. Have a successful day! 😊"
            )
            sources = ["CampusIQ Assistant"]

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

        else:
            # Query-driven institutional knowledge retrieval
            data: Dict[str, Any] = {}
            cat = match.category

            if cat == IntentCategory.COURSE_FEES.value:
                data = retriever.get_course_fees(match.target_entity)
            elif cat == IntentCategory.COURSES.value:
                if match.target_entity:
                    data = retriever.get_course_detail(match.target_entity)
                else:
                    data = retriever.get_courses_list()
            elif cat == IntentCategory.FACULTY.value:
                data = retriever.get_faculty_info(match.target_entity)
            elif cat == IntentCategory.DEPARTMENT.value:
                data = retriever.get_departments_list()
            elif cat in (
                IntentCategory.LIBRARY.value,
                IntentCategory.HOSTEL.value,
                IntentCategory.SPORTS.value,
                IntentCategory.FACILITIES.value,
            ):
                data = retriever.get_facility_info(match.target_entity)
            elif cat in (IntentCategory.ATTENDANCE.value, IntentCategory.NCC_NSS.value) or "policy" in match.intent_id:
                data = retriever.get_knowledge_document(match.intent_id)
            elif cat == IntentCategory.CONTACT.value:
                data = retriever.get_contact_info()
            else:
                data = retriever.get_college_info()

            answer_text = data.get("text", "")
            sources = data.get("sources", ["College Official Records"])
            if data.get("suggestions"):
                suggestions = data["suggestions"]

        # 5. Record bot answer in DB
        bot_msg = Message(
            conversation_id=conversation.id,
            sender="bot",
            content=answer_text,
            intent=match.intent_id,
            processing_engine=processing_engine,
            confidence_score=match.confidence,
            source_reference="; ".join(sources) if sources else None,
        )
        db.add(bot_msg)
        db.commit()

        return {
            "conversation_id": conversation.id,
            "message": answer_text,
            "intent": match.intent_id,
            "category": match.category,
            "engine": processing_engine,
            "confidence": match.confidence,
            "sources": sources,
            "suggestions": suggestions,
            "created_at": bot_msg.created_at,
        }
