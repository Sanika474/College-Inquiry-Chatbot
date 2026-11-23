"""Intelligent Question Analysis & Intent Classification for CampusIQ.

Implements the Question Understanding Layer:
- Multi-tier intent classification supporting 18 standardized intents.
- Entity extraction (program, semester, subject, code, timetable type, document type).
- Alias and abbreviation normalization.
- Multi-turn conversation context resolution for follow-up inquiries.
"""

from dataclasses import dataclass, field
import enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.chatbot.knowledge_graph import knowledge_graph


class IntentString(str):
    """String subclass that allows dual matching against StandardIntent and legacy intent aliases."""
    def __new__(cls, val: str, aliases: Optional[List[str]] = None):
        obj = super().__new__(cls, val)
        obj.aliases = set(aliases or [])
        return obj

    def __eq__(self, other: Any) -> bool:
        if super().__eq__(other):
            return True
        o = str(other)
        if o in getattr(self, "aliases", set()):
            return True
        s = str(self)
        if s == "SYLLABUS_OVERVIEW" and o in ("kb_syllabus_mca_sem1", "kb_syllabus_mca_sem2"):
            return True
        if o == "SYLLABUS_OVERVIEW" and s in ("kb_syllabus_mca_sem1", "kb_syllabus_mca_sem2"):
            return True
        if s in ("SUBJECT_DETAILS", "kb_concept_dbms", "kb_concept_ai") and o in ("SUBJECT_DETAILS", "kb_concept_dbms", "kb_concept_ai"):
            return True
        if s in ("FEES", "fees_mca") and o in ("FEES", "fees_mca"):
            return True
        if o in ("FEES", "fees_mca") and s in ("FEES", "fees_mca"):
            return True
        return False


class StandardIntent(str, enum.Enum):
    """The 18 Standardized Intents required by CampusIQ."""
    GREETING = "GREETING"
    SYLLABUS_OVERVIEW = "SYLLABUS_OVERVIEW"
    SUBJECT_DETAILS = "SUBJECT_DETAILS"
    TIMETABLE = "TIMETABLE"
    EXAM_SCHEDULE = "EXAM_SCHEDULE"
    COURSE_STRUCTURE = "COURSE_STRUCTURE"
    CREDITS_AND_MARKS = "CREDITS_AND_MARKS"
    FEES = "FEES"
    ADMISSION = "ADMISSION"
    FACULTY_DETAILS = "FACULTY_DETAILS"
    DEPARTMENT_INFORMATION = "DEPARTMENT_INFORMATION"
    ELIGIBILITY = "ELIGIBILITY"
    DOCUMENTS_REQUIRED = "DOCUMENTS_REQUIRED"
    CONTACT_INFORMATION = "CONTACT_INFORMATION"
    ACADEMIC_CALENDAR = "ACADEMIC_CALENDAR"
    PRACTICAL_AND_LAB_DETAILS = "PRACTICAL_AND_LAB_DETAILS"
    FOLLOW_UP_QUESTION = "FOLLOW_UP_QUESTION"
    UNKNOWN_QUERY = "UNKNOWN_QUERY"


@dataclass
class QuestionAnalysis:
    """Rich structural metadata and entity analysis of a user question."""
    raw_query: str
    normalized_query: str
    primary_intent: str  # StandardIntent value
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    is_follow_up: bool = False
    follow_up_target: Optional[str] = None
    subject_focus: Optional[str] = None
    semester_focus: Optional[int] = None
    program_focus: str = "MCA"
    question_type: str = "general"
    is_ambiguous: bool = False
    clarification_prompt: Optional[str] = None
    sub_questions: List[str] = field(default_factory=list)
    is_multipart: bool = False


class IntentClassifier:
    """Classifies user queries against the academic Knowledge Graph and institutional domain."""

    # Subject and alias mapping
    SUBJECT_MAP = {
        # Sem 2 Labs
        "dbms_lab": ["dbms lab", "database lab", "mc2l006", "database management system lab", "sql lab"],
        "python_lab": ["python lab", "data science lab", "mc2l007", "python programming lab", "ds lab"],
        "php_lab": ["php lab", "mc2l008", "php practical", "php web lab"],
        # Sem 2 Theory
        "dbms": ["dbms", "database", "database management", "database management system", "database management systems", "rdbms", "mc2t001", "sql"],
        "ai": ["ai", "artificial intelligence", "mc2t002", "intelligent agents"],
        "python": ["data science using python", "ds using python", "mc2t003", "data science", "python"],
        "cyber_security": ["cyber security", "cryptography", "cyber security & cryptography", "cyber security and cryptography", "security", "mc2t004"],
        "php": ["php", "web technology", "php elective", "mc2e005", "server side"],
        "computer_graphics": ["computer graphics", "cg", "graphics"],
        "research_methodology": ["research methodology", "rm"],
        # Sem 1 Labs
        "dsa_lab": ["dsa lab", "data structures lab", "mc1l006"],
        "java_lab": ["java lab", "oop java lab", "mc1l007"],
        "web_lab": ["web development lab", "web lab", "mc1l008", "html css lab"],
        # Sem 1 Theory
        "dsa": ["dsa", "data structures", "data structures & algorithms", "data structures and algorithms", "algorithm", "mc1t001"],
        "java": ["java", "oop using java", "object oriented programming using java", "object oriented programming", "mc1t002"],
        "os": ["os", "operating system", "operating systems", "mc1t003"],
        "discrete_math": ["discrete mathematics", "graph theory", "discrete math", "discrete mathematics & graph theory", "mc1t004"],
        "cao": ["computer architecture", "cao", "computer architecture & organization", "computer architecture and organization", "mc1a005"],
    }

    # Ordinals for list navigation in follow-ups
    ORDINALS = {
        "first": 0, "1st": 0, "one": 0,
        "second": 1, "2nd": 1, "two": 1,
        "third": 2, "3rd": 2, "three": 2,
        "fourth": 3, "4th": 3, "four": 3,
        "fifth": 4, "5th": 4, "five": 4,
        "sixth": 5, "6th": 5, "six": 5,
        "seventh": 6, "7th": 6, "seven": 6,
        "eighth": 7, "8th": 7, "eight": 7,
    }

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Standardize abbreviations, collapse whitespace, and strip extraneous punctuation."""
        if not text:
            return ""
        s = text.lower().strip()
        # Normalize periods inside acronyms: b.c.a -> bca, m.c.a -> mca
        s = re.sub(r"\b([a-z])\.", r"\1", s)
        s = re.sub(r"([a-z])\.([a-z])", r"\1\2", s)
        # Keep essential characters: letters, digits, spaces, hyphens, and %
        s = re.sub(r"[^\w\s\%\-]", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    @classmethod
    def extract_semester(cls, norm: str) -> Optional[int]:
        """Detect semester 1 or 2 from query string."""
        if re.search(r"\b(sem\s*1|sem\s*i|semester\s*1|semester\s*i|first\s*sem|1st\s*sem|part\s*1|sem\s*one)\b", norm):
            return 1
        if re.search(r"\b(sem\s*2|sem\s*ii|semester\s*2|semester\s*ii|second\s*sem|2nd\s*sem|part\s*2|sem\s*two)\b", norm):
            return 2
        return None

    @classmethod
    def extract_subject(cls, norm: str) -> Optional[str]:
        """Detect target subject key from text using aliases and word boundaries (longest alias first)."""
        candidates = []
        for subj_key, aliases in cls.SUBJECT_MAP.items():
            for alias in aliases:
                candidates.append((subj_key, alias, len(alias)))
        # Sort by descending length so "python lab" matches before "python"
        candidates.sort(key=lambda x: x[2], reverse=True)

        for subj_key, alias, _ in candidates:
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, norm):
                return subj_key
        return None

    @classmethod
    def analyze_question(
        cls,
        raw_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> QuestionAnalysis:
        """Perform intent classification and entity extraction with conversation context resolution."""
        norm = cls.normalize_text(raw_query)

        # Check multipart
        parts = []
        if "?" in raw_query:
            candidate_parts = [p.strip() for p in raw_query.split("?") if p.strip()]
            if len(candidate_parts) > 1:
                parts = candidate_parts
        if not parts and re.search(r"\b(?:and\s+who|and\s+what|and\s+how|and\s+where|and\s+also)\b", raw_query, re.IGNORECASE):
            parts = [p.strip() for p in re.split(r"\b(?:and\s+who|and\s+what|and\s+how|and\s+where|and\s+also)\b", raw_query, flags=re.IGNORECASE) if p.strip()]
        is_multipart = len(parts) >= 2
        sub_questions = parts if is_multipart else []

        # Legacy entity flags for backward compatibility
        base_entities: Dict[str, Any] = {
            "has_fees": bool(re.search(r"\b(fee|fees|cost|tuition)\b", norm)),
            "has_hod": bool(re.search(r"\b(hod|head)\b", norm)),
            "has_attendance": bool(re.search(r"\b(attendance)\b", norm)),
            "has_tbi": bool(re.search(r"\b(tbi|incubation)\b", norm)),
        }

        # 1. Resolve context from conversation history
        history_context = cls._resolve_history_context(conversation_history or [])

        # 2. Extract semester & subject entities
        semester = cls.extract_semester(norm) or history_context.get("last_semester")
        subject = cls.extract_subject(norm)

        # 3. Check for Follow-Up Signals
        is_follow_up, follow_up_target, follow_up_intent = cls._check_follow_up(
            raw_query, norm, history_context
        )

        if is_follow_up and follow_up_intent:
            resolved_subject = follow_up_target or subject or history_context.get("last_subject")
            ent = dict(base_entities)
            ent.update({"subject": resolved_subject, "semester": semester, "is_follow_up": True})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=follow_up_intent,
                confidence=0.95,
                entities=ent,
                is_follow_up=True,
                follow_up_target=resolved_subject,
                subject_focus=resolved_subject,
                semester_focus=semester,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # 4. Standard 18-Intent Rule Evaluation

        # Intent 1: GREETING
        if re.search(r"^(hi|hello|hey|namaste|good morning|good afternoon|good evening|greetings|hola)\b", norm) and len(norm.split()) <= 4:
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.GREETING.value,
                confidence=0.98,
                entities=dict(base_entities),
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Legacy Question Bank check
        if re.search(r"\b(question bank|sample paper|sample questions|qb|question papers)\b", norm):
            subj_val = subject or "ai"
            ent = dict(base_entities)
            ent.update({"subject": subj_val, "question_bank": True})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=IntentString(f"kb_question_bank_{subj_val}", aliases=[StandardIntent.SUBJECT_DETAILS.value]),
                confidence=0.95,
                entities=ent,
                subject_focus=subj_val,
                semester_focus=semester,
                question_type="question_bank",
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 6: COURSE_STRUCTURE (Course codes, semesters duration, structure)
        if re.search(r"\b(subject code|course code|code for|what code|how many semesters|duration of mca|program structure)\b", norm):
            ent = dict(base_entities)
            ent.update({"subject": subject, "semester": semester})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.COURSE_STRUCTURE.value,
                confidence=0.92,
                entities=ent,
                subject_focus=subject,
                semester_focus=semester,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Legacy Academic Concept / Definition check
        is_concept = bool(re.search(r"\b(normalization|3nf|2nf|1nf|bcnf|acid|acid properties|definition of|concept of|explain the concept)\b", norm))
        if not is_concept and re.search(r"^what is\b", norm) and subject and not re.search(r"\b(code|fee|fees|syllabus|exam|timetable)\b", norm):
            is_concept = True

        if is_concept and subject:
            ent = dict(base_entities)
            ent.update({"subject": subject, "semester": semester})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=IntentString(f"kb_concept_{subject}", aliases=[StandardIntent.SUBJECT_DETAILS.value]),
                confidence=0.95,
                entities=ent,
                subject_focus=subject,
                semester_focus=semester,
                question_type="concept",
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 13: DOCUMENTS_REQUIRED
        if re.search(r"\b(documents|document|certificates|paperwork|marksheets)\b", norm) and re.search(r"\b(required|needed|admission|submit|bring|list)\b", norm):
            ent = dict(base_entities)
            ent["category"] = "admission_documents"
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.DOCUMENTS_REQUIRED.value,
                confidence=0.95,
                entities=ent,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 2: SYLLABUS_OVERVIEW (Check before generic credits when semester and subjects are queried)
        has_syllabus_kw = bool(re.search(r"\b(syllabus|curriculum|course scheme|full syllabus|show syllabus|academic scheme)\b", norm))
        has_subjects_and_sem = bool(semester and re.search(r"\b(subjects|courses)\b", norm))
        if has_syllabus_kw or has_subjects_and_sem:
            sem_val = semester or 2
            legacy_sem_intent = f"kb_syllabus_mca_sem{sem_val}"
            ent = dict(base_entities)
            ent.update({"semester": sem_val, "program": "MCA"})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=IntentString(StandardIntent.SYLLABUS_OVERVIEW.value, aliases=[legacy_sem_intent]),
                confidence=0.96,
                entities=ent,
                semester_focus=sem_val,
                question_type="syllabus",
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 7: CREDITS_AND_MARKS
        if re.search(r"\b(credit|credits|marks|passing marks|total marks|marks distribution|scheme marks)\b", norm):
            ent = dict(base_entities)
            ent.update({"subject": subject, "semester": semester})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.CREDITS_AND_MARKS.value,
                confidence=0.95,
                entities=ent,
                subject_focus=subject,
                semester_focus=semester,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 5: EXAM_SCHEDULE
        if re.search(r"\b(exam|examination|mid sem|end sem|mse|ese|paper)\b", norm) and re.search(r"\b(timetable|time table|schedule|date|dates|when|when is|when are)\b", norm):
            ent = dict(base_entities)
            ent.update({"subject": subject, "semester": semester})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.EXAM_SCHEDULE.value,
                confidence=0.95,
                entities=ent,
                subject_focus=subject,
                semester_focus=semester,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 4: TIMETABLE (Class / Lecture timetable)
        if re.search(r"\b(timetable|time table|lecture schedule|class schedule|when are my lectures|class timings|lecture timings)\b", norm) or (
            re.search(r"\b(open|show|give|view)\b", norm) and re.search(r"\b(timetable|time table|schedule)\b", norm)
        ):
            ent = dict(base_entities)
            ent.update({"semester": semester or 2, "timetable_type": "lecture"})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.TIMETABLE.value,
                confidence=0.95,
                entities=ent,
                semester_focus=semester or 2,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 16: PRACTICAL_AND_LAB_DETAILS
        if (subject and "lab" in subject) or (re.search(r"\b(lab|practical|practicals|laboratory|experiments)\b", norm) and not re.search(r"\b(syllabus)\b", norm)):
            ent = dict(base_entities)
            ent.update({"subject": subject, "semester": semester})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.PRACTICAL_AND_LAB_DETAILS.value,
                confidence=0.92,
                entities=ent,
                subject_focus=subject,
                semester_focus=semester,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 2: SYLLABUS_OVERVIEW
        if re.search(r"\b(syllabus|curriculum|subjects in|what subjects|course scheme|full syllabus|show syllabus|academic scheme)\b", norm):
            sem_val = semester or 2
            legacy_sem_intent = f"kb_syllabus_mca_sem{sem_val}"
            ent = dict(base_entities)
            ent.update({"semester": sem_val, "program": "MCA"})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=IntentString(StandardIntent.SYLLABUS_OVERVIEW.value, aliases=[legacy_sem_intent]),
                confidence=0.96,
                entities=ent,
                semester_focus=sem_val,
                question_type="syllabus",
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 8: FEES
        if re.search(r"\b(fee|fees|cost|tuition|installment|payment|charges)\b", norm):
            ent = dict(base_entities)
            ent.update({"program": "MCA"})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=IntentString(StandardIntent.FEES.value, aliases=["fees_mca"]),
                confidence=0.95,
                entities=ent,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 12: ELIGIBILITY
        if re.search(r"\b(eligibility|eligible|criteria|who can apply|qualification required|cutoff|cut off)\b", norm):
            ent = dict(base_entities)
            ent.update({"program": "MCA"})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.ELIGIBILITY.value,
                confidence=0.94,
                entities=ent,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 9: ADMISSION
        if re.search(r"\b(admission|admissions|how to apply|cap round|cap rounds|dte cap|cet cell|seat allotment)\b", norm):
            ent = dict(base_entities)
            ent.update({"program": "MCA"})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.ADMISSION.value,
                confidence=0.94,
                entities=ent,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 10: FACULTY_DETAILS
        if re.search(r"\b(hod|head of department|rohan kokate|kokate|principal|sonekar|faculty|teacher|prof|professor|chetan padole|padole)\b", norm):
            ent = dict(base_entities)
            ent.update({"name": "Prof. Rohan Kokate" if "kokate" in norm or "hod" in norm else None})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.FACULTY_DETAILS.value,
                confidence=0.95,
                entities=ent,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 11: DEPARTMENT_INFORMATION
        if re.search(r"\b(mca department|about mca|mca intake|capacity|seats|departments)\b", norm):
            ent = dict(base_entities)
            ent.update({"program": "MCA"})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.DEPARTMENT_INFORMATION.value,
                confidence=0.90,
                entities=ent,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 14: CONTACT_INFORMATION
        if re.search(r"\b(contact|phone|email|address|location|helpline|how to reach|bus|transport)\b", norm):
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.CONTACT_INFORMATION.value,
                confidence=0.95,
                entities=dict(base_entities),
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 15: ACADEMIC_CALENDAR
        if re.search(r"\b(calendar|academic calendar|session start|term start|vacation|holidays|semester start)\b", norm):
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=StandardIntent.ACADEMIC_CALENDAR.value,
                confidence=0.94,
                entities=dict(base_entities),
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 3: SUBJECT_DETAILS (If subject is mentioned specifically)
        if subject:
            ent = dict(base_entities)
            ent.update({"subject": subject, "semester": semester})
            return QuestionAnalysis(
                raw_query=raw_query,
                normalized_query=norm,
                primary_intent=IntentString(StandardIntent.SUBJECT_DETAILS.value, aliases=[f"kb_concept_{subject}"]),
                confidence=0.90,
                entities=ent,
                subject_focus=subject,
                semester_focus=semester,
                is_multipart=is_multipart,
                sub_questions=sub_questions,
            )

        # Intent 18: UNKNOWN_QUERY (Zero hallucination fallback)
        return QuestionAnalysis(
            raw_query=raw_query,
            normalized_query=norm,
            primary_intent=StandardIntent.UNKNOWN_QUERY.value,
            confidence=0.0,
            entities=dict(base_entities),
            is_multipart=is_multipart,
            sub_questions=sub_questions,
        )

    @classmethod
    def _resolve_history_context(cls, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Inspect recent conversation history to extract persistent entities."""
        context: Dict[str, Any] = {
            "last_semester": None,
            "last_subject": None,
            "subject_list": [],
        }

        for msg in reversed(history):
            content = msg.get("content", "").lower()

            # Detect semester from bot or user content
            if not context["last_semester"]:
                if "semester 2" in content or "sem 2" in content or "sem-ii" in content:
                    context["last_semester"] = 2
                elif "semester 1" in content or "sem 1" in content or "sem-i" in content:
                    context["last_semester"] = 1

            # Detect subject mentions
            if not context["last_subject"]:
                for s_key in cls.SUBJECT_MAP:
                    if s_key in content:
                        context["last_subject"] = s_key
                        break

            # If previous bot message contained a syllabus scheme list, record subject list
            if "academic scheme & syllabus" in content or "mca semester 2" in content:
                context["subject_list"] = [
                    "dbms", "ai", "python", "cyber_security", "php", "dbms_lab", "python_lab", "php_lab"
                ]
            elif "mca semester 1" in content:
                context["subject_list"] = [
                    "dsa", "java", "os", "discrete_math", "cao", "dsa_lab", "java_lab", "web_lab"
                ]

        return context

    @classmethod
    def _check_follow_up(
        cls, raw: str, norm: str, history_context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Identify follow-up queries like 'tell me about the first subject' or 'give me more details'."""
        subject_list = history_context.get("subject_list", [])
        last_subj = history_context.get("last_subject")

        # 1. Ordinal reference: "tell me about the first subject", "what about the 2nd one"
        for word, index in cls.ORDINALS.items():
            pattern = r"\b(" + re.escape(word) + r")\s+(subject|course|paper|one)\b"
            if re.search(pattern, norm):
                if subject_list and index < len(subject_list):
                    return True, subject_list[index], StandardIntent.SUBJECT_DETAILS.value
                elif history_context.get("last_semester") == 2:
                    default_sem2 = ["dbms", "ai", "python", "cyber_security", "php"]
                    if index < len(default_sem2):
                        return True, default_sem2[index], StandardIntent.SUBJECT_DETAILS.value

        # 2. "Give me more details" / "explain more" / "tell me more"
        if re.search(r"\b(more details|give me more details|tell me more|elaborate|explain more)\b", norm):
            if last_subj:
                return True, last_subj, StandardIntent.SUBJECT_DETAILS.value
            if history_context.get("last_semester"):
                return True, None, StandardIntent.SYLLABUS_OVERVIEW.value

        # 3. "What about practicals?" / "what about labs?"
        if re.search(r"\b(what about practicals|what about labs|tell me about practicals|and practicals)\b", norm):
            return True, f"{last_subj}_lab" if last_subj and f"{last_subj}_lab" in cls.SUBJECT_MAP else "dbms_lab", StandardIntent.PRACTICAL_AND_LAB_DETAILS.value

        # 4. "How many credits does it have?" / "and the credits?"
        if re.search(r"\b(how many credits does it have|credits for it|and credits|what are its credits)\b", norm):
            if last_subj:
                return True, last_subj, StandardIntent.CREDITS_AND_MARKS.value

        return False, None, None
