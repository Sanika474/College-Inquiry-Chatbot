"""Intelligent Question Analysis & Intent Classification for CampusIQ.

Distinguishes between question types (definitions, procedures, fee structures,
academic syllabus, lecture notes, question banks, comparisons, multi-part,
and follow-up queries) with confidence scoring and ambiguity detection.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class QuestionAnalysis:
    """Rich metadata analysis of a user question."""

    def __init__(
        self,
        raw_query: str,
        normalized_query: str,
        primary_intent: str,
        question_type: str,  # definition, procedural, fee, syllabus, concept, question_bank, comparison, multipart, follow_up, general
        confidence: float,
        entities: Dict[str, Any],
        is_multipart: bool = False,
        sub_questions: Optional[List[str]] = None,
        is_ambiguous: bool = False,
        competing_intents: Optional[List[Tuple[str, float]]] = None,
        is_follow_up: bool = False,
        subject_focus: Optional[str] = None,  # dbms, dsa, os, cloud, graph_theory, php, ai, etc.
        semester_focus: Optional[int] = None,  # 1 or 2
    ):
        self.raw_query = raw_query
        self.normalized_query = normalized_query
        self.primary_intent = primary_intent
        self.question_type = question_type
        self.confidence = confidence
        self.entities = entities
        self.is_multipart = is_multipart
        self.sub_questions = sub_questions or []
        self.is_ambiguous = is_ambiguous
        self.competing_intents = competing_intents or []
        self.is_follow_up = is_follow_up
        self.subject_focus = subject_focus
        self.semester_focus = semester_focus

    def __repr__(self) -> str:
        return f"<QuestionAnalysis intent='{self.primary_intent}' type='{self.question_type}' conf={self.confidence:.2f}>"


class IntentClassifier:
    """Classifies user queries against academic knowledge base and institutional intents."""

    # Academic subjects present in Knowledge_Base
    SUBJECT_KEYWORDS = {
        "dbms": [
            "dbms",
            "database",
            "rdbms",
            "sql",
            "relational algebra",
            "acid",
            "normalization",
            "1nf",
            "2nf",
            "3nf",
            "bcnf",
            "er model",
            "concurrency control",
            "transactions",
            "keys",
            "primary key",
        ],
        "dsa": [
            "dsa",
            "data structure",
            "data structures",
            "algorithm",
            "algorithms",
            "stack",
            "queue",
            "linked list",
            "binary tree",
            "sorting",
            "searching",
            "linear search",
            "binary search",
            "bubble sort",
            "quick sort",
            "merge sort",
            "avl",
        ],
        "os": [
            "operating system",
            "operating systems",
            "os",
            "process",
            "scheduling",
            "deadlock",
            "deadlocks",
            "virtual memory",
            "paging",
            "segmentation",
            "page replacement",
            "semaphore",
            "inter-process communication",
        ],
        "cloud": [
            "cloud",
            "cloud computing",
            "iaas",
            "paas",
            "saas",
            "virtualization",
            "hypervisor",
            "public cloud",
            "private cloud",
            "hybrid cloud",
            "nist",
            "scalability",
        ],
        "discrete_math": [
            "discrete",
            "discrete mathematics",
            "graph theory",
            "euler graph",
            "hamiltonian",
            "planar graph",
            "trees",
            "isomorphism",
            "coloring",
            "recurrence relation",
        ],
        "php": [
            "php",
            "web technology",
            "php unit",
            "superglobals",
            "server-side",
            "arrays in php",
        ],
        "ai": [
            "artificial intelligence",
            "ai",
            "agent",
            "heuristic search",
            "a*",
            "minimax",
            "alpha-beta",
            "knowledge representation",
            "expert systems",
        ],
    }

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Lowercase, strip extraneous punctuation, collapse whitespace."""
        if not text:
            return ""
        s = text.lower().strip()
        # Preserve characters: alphanumeric, spaces, and essential symbols like %, ?
        s = re.sub(r"[^\w\s\%\?\-]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @classmethod
    def analyze_question(
        cls, raw_query: str, conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> QuestionAnalysis:
        """Perform comprehensive classification and structural analysis on user query."""
        norm = cls.normalize_text(raw_query)

        # 1. Detect follow-up signals
        is_follow_up, follow_up_context = cls._detect_follow_up(
            raw_query, norm, conversation_history
        )

        # 2. Extract semester focus (1 or 2)
        semester_focus = None
        if re.search(r"\b(sem\s*1|sem\s*i|semester\s*1|semester\s*i|first\s*sem|1st\s*sem)\b", norm):
            semester_focus = 1
        elif re.search(r"\b(sem\s*2|sem\s*ii|semester\s*2|semester\s*ii|second\s*sem|2nd\s*sem)\b", norm):
            semester_focus = 2
        elif is_follow_up and follow_up_context and "semester" in follow_up_context:
            semester_focus = follow_up_context["semester"]

        # 3. Extract subject focus
        subject_focus = cls._detect_subject_focus(norm)
        if not subject_focus and is_follow_up and follow_up_context and "subject" in follow_up_context:
            subject_focus = follow_up_context["subject"]

        # 4. Detect multi-part inquiries
        is_multipart, sub_questions = cls._detect_multipart(raw_query, norm)

        # 5. Detect question type
        question_type = cls._detect_question_type(norm, subject_focus, is_multipart)

        # 6. Intent classification with confidence scoring
        primary_intent, confidence, competing = cls._classify_intent(
            norm, subject_focus, semester_focus, question_type, is_follow_up
        )

        # 7. Check ambiguity
        is_ambiguous = False
        if len(competing) >= 2 and (competing[0][1] - competing[1][1] < 0.12) and competing[0][1] < 0.85:
            is_ambiguous = True

        entities = {
            "semester": semester_focus,
            "subject": subject_focus,
            "raw_subject": subject_focus,
            "has_fees": bool(re.search(r"\b(fee|fees|cost|tuition)\b", norm)),
            "has_hod": bool(re.search(r"\b(hod|head|rohan|kokate)\b", norm)),
            "has_attendance": bool(re.search(r"\b(attendance|75%|75\s*percent)\b", norm)),
            "has_tbi": bool(re.search(r"\b(tbi|incubat|startup|chetan|padole)\b", norm)),
        }

        return QuestionAnalysis(
            raw_query=raw_query,
            normalized_query=norm,
            primary_intent=primary_intent,
            question_type=question_type,
            confidence=confidence,
            entities=entities,
            is_multipart=is_multipart,
            sub_questions=sub_questions,
            is_ambiguous=is_ambiguous,
            competing_intents=competing,
            is_follow_up=is_follow_up,
            subject_focus=subject_focus,
            semester_focus=semester_focus,
        )

    @classmethod
    def _detect_subject_focus(cls, norm: str) -> Optional[str]:
        """Detect which Knowledge_Base subject is being targeted."""
        for subj, kw_list in cls.SUBJECT_KEYWORDS.items():
            for kw in kw_list:
                pattern = r"\b" + re.escape(kw) + r"\b"
                if re.search(pattern, norm):
                    return subj
        return None

    @classmethod
    def _detect_multipart(cls, raw: str, norm: str) -> Tuple[bool, List[str]]:
        """Identify multi-part questions (e.g. 'What are the MCA fees and who is the HOD?')."""
        # Multi-question marks
        parts = [p.strip() for p in raw.split("?") if p.strip()]
        if len(parts) >= 2:
            return True, [p + "?" for p in parts]

        # Conjunction splitters
        splitters = [" and also ", " as well as ", " and what is ", " and who is ", " and tell me about "]
        for s in splitters:
            if s in norm:
                sub = norm.split(s)
                if len(sub) == 2 and len(sub[0]) > 10 and len(sub[1]) > 10:
                    return True, [sub[0].strip(), sub[1].strip()]

        return False, []

    @classmethod
    def _detect_question_type(
        cls, norm: str, subject_focus: Optional[str], is_multipart: bool
    ) -> str:
        """Classify question structure and functional type."""
        if is_multipart:
            return "multipart"

        # Comparison
        if re.search(r"\b(difference between|compare|versus|\bvs\b|comparison)\b", norm):
            return "comparison"

        # Question Bank / Exam Prep
        if re.search(r"\b(question bank|questions bank|sample questions|important questions|exam questions|previous year)\b", norm):
            return "question_bank"

        # Syllabus / Course Structure
        if re.search(r"\b(syllabus|curriculum|scheme|subjects|course code|credits|credit|marks distribution)\b", norm):
            return "syllabus"

        # Fee Structure
        if re.search(r"\b(fee|fees|cost|tuition|development fee|fra|scholarship)\b", norm):
            return "fee"

        # Procedural / How to
        if re.search(r"\b(how to|procedure|steps to|process of|guidelines for|how can i)\b", norm):
            return "procedural"

        # Definition / Concept explanation
        if re.search(r"\b(what is|define|explain|what are|meaning of|concept of)\b", norm) and subject_focus:
            return "concept"
        elif re.search(r"\b(what is|define|meaning of)\b", norm):
            return "definition"

        if subject_focus:
            return "concept"

        return "general"

    @classmethod
    def _detect_follow_up(
        cls, raw: str, norm: str, history: Optional[List[Dict[str, str]]]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Detect pronoun/anaphoric references relying on previous turns."""
        if not history:
            return False, None

        follow_up_cues = [
            r"^(what about|and what about|how about)\b",
            r"\b(its|it's|their|this course|that subject|that course|the same)\b",
            r"^(who teaches it|who is the hod|what are the reference books|what are its credits)\b",
        ]
        is_cue = any(re.search(pat, norm) for pat in follow_up_cues)
        if not is_cue and len(norm.split()) > 7:
            return False, None

        # Look back at last assistant/user message for context
        context: Dict[str, Any] = {}
        for msg in reversed(history[-4:]):
            text = (msg.get("content") or "").lower()
            # Extract previous subject
            for subj, kw_list in cls.SUBJECT_KEYWORDS.items():
                if any(kw in text for kw in kw_list):
                    context["subject"] = subj
                    break
            # Extract previous semester
            if "sem 1" in text or "semester 1" in text:
                context["semester"] = 1
            elif "sem 2" in text or "semester 2" in text:
                context["semester"] = 2

            if context:
                return True, context

        return is_cue, context if context else None

    @classmethod
    def _classify_intent(
        cls,
        norm: str,
        subject_focus: Optional[str],
        semester_focus: Optional[int],
        question_type: str,
        is_follow_up: bool,
    ) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Score candidate intents with specific intents outranking generic intents."""
        scored: List[Tuple[str, float]] = []

        # 1. Question Bank intents (Specific)
        if question_type == "question_bank" or re.search(r"\b(question bank|questions bank)\b", norm):
            if subject_focus == "ai":
                scored.append(("kb_question_bank_ai", 0.96))
            elif subject_focus == "php":
                scored.append(("kb_question_bank_php", 0.96))
            elif subject_focus == "dbms":
                scored.append(("kb_question_bank_dbms", 0.96))
            else:
                scored.append(("kb_question_bank_general", 0.88))

        # 2. Syllabus specific Sem 1 vs Sem 2
        if semester_focus == 1 and ("syllabus" in norm or "subject" in norm or "scheme" in norm):
            scored.append(("kb_syllabus_mca_sem1", 0.95))
        elif semester_focus == 2 and ("syllabus" in norm or "subject" in norm or "scheme" in norm):
            scored.append(("kb_syllabus_mca_sem2", 0.95))
        elif "syllabus" in norm or "scheme" in norm:
            scored.append(("kb_syllabus_mca_general", 0.85))

        # 3. Academic Concept inquiries from Notes/Books
        if subject_focus:
            conf = 0.92 if question_type in ("concept", "definition") else 0.82
            scored.append((f"kb_concept_{subject_focus}", conf))

        # 4. Institutional Core Intents
        if re.search(r"\b(fee|fees|cost|tuition|charge|structure|fra)\b", norm):
            if "btech" in norm or "engineering" in norm and "mca" not in norm:
                scored.append(("fee_btech", 0.92))
            else:
                scored.append(("fee_mca", 0.95))

        if re.search(r"\b(hod|head of department|rohan|kokate)\b", norm):
            scored.append(("faculty_mca", 0.96))

        if re.search(r"\b(principal|sonekar|head of college)\b", norm):
            scored.append(("college_principal", 0.95))

        if re.search(r"\b(attendance|75%|75\s*percent|absenteeism)\b", norm):
            scored.append(("policy_attendance", 0.96))

        if re.search(r"\b(tbi|incubation|incubator|startup|entrepreneur|chetan|padole)\b", norm):
            scored.append(("facility_tbi", 0.95))

        if re.search(r"\b(placement|package|recruiter|placed|salary)\b", norm):
            scored.append(("placement_highlights", 0.92))

        if re.search(r"\b(dte|dte code|04138|dbatu|autonomous|naac)\b", norm):
            scored.append(("college_overview", 0.92))

        if re.search(r"\b(admission|cap round|eligibility|cet|mah mca cet|intake|seats)\b", norm):
            scored.append(("admission_mca", 0.92))

        # 5. Greetings & Conversation Starters
        if re.search(r"^(hi|hello|hey|namaste|good morning|good afternoon|good evening)\b", norm):
            scored.append(("greeting", 0.98))

        if re.search(r"\b(bye|goodbye|see you|thank you|thanks)\b", norm):
            scored.append(("farewell", 0.98))

        # Sort candidate scores descending
        scored.sort(key=lambda x: x[1], reverse=True)

        if scored:
            top_intent, top_score = scored[0]
            return top_intent, top_score, scored

        # Fallback out of domain
        return "general_knowledge_search", 0.45, [("general_knowledge_search", 0.45)]
