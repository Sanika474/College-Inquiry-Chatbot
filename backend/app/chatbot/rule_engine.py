"""Deterministic Rule-Based Chatbot Engine for CampusIQ.

Classifies user inquiries, extracts target entities, evaluates priority-weighted rules,
and identifies underspecified or ambiguous queries.
"""

from dataclasses import dataclass, field
import re
from typing import List, Optional, Set, Tuple

from app.chatbot.intent_catalog import INTENT_CATALOG, IntentCategory, IntentDefinition


@dataclass
class RuleMatchResult:
    """Outcome of intent rule classification."""

    intent_id: str
    category: str
    confidence: float
    target_entity: Optional[str] = None
    is_ambiguous: bool = False
    clarification_prompt: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


class RuleEngine:
    """High-precision, deterministic pattern and keyword classifier."""

    def __init__(self, catalog: Optional[List[IntentDefinition]] = None):
        # Sort catalog by descending priority tier
        self.catalog = sorted(catalog or INTENT_CATALOG, key=lambda x: x.priority, reverse=True)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Standardize abbreviations (e.g., B.C.A. -> bca), strip punctuation, and trim spaces."""
        if not text:
            return ""
        # Remove period dots inside acronyms (B.C.A. -> BCA, B.Sc. -> BSc)
        cleaned = re.sub(r"\b([a-zA-Z])\.", r"\1", text)
        cleaned = re.sub(r"([a-zA-Z])\.([a-zA-Z])", r"\1\2", cleaned)
        cleaned = cleaned.lower()
        # Replace non-alphanumeric chars (excluding spaces) with space
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        # Collapse multiple whitespace
        return re.sub(r"\s+", " ", cleaned).strip()

    def classify(self, raw_query: str) -> RuleMatchResult:
        """Analyze raw inquiry and return highest-scoring intent match."""
        if not raw_query or not raw_query.strip():
            return RuleMatchResult(
                intent_id="empty_query",
                category=IntentCategory.UNKNOWN.value,
                confidence=0.0,
                clarification_prompt="How can I assist you with college inquiries today?",
                suggestions=["Courses offered", "Fee structure", "Hostel facilities", "Principal contact"],
            )

        norm_query = self.normalize_text(raw_query)
        tokens: Set[str] = set(norm_query.split())

        candidates: List[Tuple[IntentDefinition, float]] = []

        for intent in self.catalog:
            confidence = 0.0

            # 1. Regex pattern matching
            if intent.patterns:
                for pattern in intent.patterns:
                    # Check against both raw query and normalized query
                    if pattern.search(raw_query) or pattern.search(norm_query):
                        confidence = max(confidence, 0.95)
                        break

            # 2. Keyword matching
            has_keywords_all = bool(intent.keywords_all)
            has_keywords_any = bool(intent.keywords_any)

            if has_keywords_all or has_keywords_any:
                all_matched = True
                if has_keywords_all:
                    for kw in intent.keywords_all:
                        kw_norm = self.normalize_text(kw)
                        if kw_norm not in norm_query and kw_norm not in tokens:
                            all_matched = False
                            break

                any_matched = False
                if has_keywords_any:
                    for kw in intent.keywords_any:
                        kw_norm = self.normalize_text(kw)
                        # Check either word boundary in query or exact token in set
                        if re.search(r"\b" + re.escape(kw_norm) + r"\b", norm_query) or kw_norm in tokens:
                            any_matched = True
                            break
                else:
                    any_matched = True  # Not required

                if all_matched and any_matched:
                    # High keyword confidence
                    confidence = max(confidence, 0.90)

            if confidence >= 0.70:
                candidates.append((intent, confidence))

        if not candidates:
            return RuleMatchResult(
                intent_id="unknown",
                category=IntentCategory.UNKNOWN.value,
                confidence=0.0,
                clarification_prompt=(
                    "I couldn't locate specific information for that query in our JDCOEM handbook. "
                    "You can try asking about our MCA department, fees, faculty, TBI incubation, or campus facilities."
                ),
                suggestions=["MCA Course Fees", "MCA Admission Eligibility", "Prof. Rohan Kokate (HOD MCA)", "TBI Startup Incubation"],
            )

        # Select highest priority candidate (catalog was pre-sorted by priority descending)
        # In case of tie, sort by priority * 100 + confidence
        best_intent, best_confidence = max(candidates, key=lambda c: (c[0].priority, c[1]))

        # Ambiguity / Clarification check:
        # If user asks just "fees" or "fee structure" without course specification
        if best_intent.intent_id == "fees_general" and len(tokens) <= 3:
            return RuleMatchResult(
                intent_id="fees_general",
                category=best_intent.category.value,
                confidence=best_confidence,
                target_entity=None,
                is_ambiguous=True,
                clarification_prompt=(
                    "JDCOEM offers multiple autonomous programs including MCA, B.Tech, and MBA. "
                    "Which course fee would you like to review?"
                ),
                suggestions=["MCA Fees", "B.Tech CSE Fees", "MBA Fees", "Hostel Fees"],
            )

        # Default suggestions based on category
        suggestions = self._build_suggestions(best_intent)

        return RuleMatchResult(
            intent_id=best_intent.intent_id,
            category=best_intent.category.value,
            confidence=best_confidence,
            target_entity=best_intent.target_entity,
            suggestions=suggestions,
        )

    @staticmethod
    def _build_suggestions(intent: IntentDefinition) -> List[str]:
        """Generate helpful contextual next-turn inquiry chips."""
        cat = intent.category
        if cat == IntentCategory.GREETING:
            return ["MCA Course Details", "MCA Fees (FRA Sanctioned)", "Prof. Rohan Kokate (HOD MCA)", "TBI Startup Incubation"]
        elif cat == IntentCategory.COURSE_FEES:
            return ["MCA Eligibility & MAH-CET", "Hostel & Bus Fees", "State Scholarships", "DTE Code: 04138"]
        elif cat == IntentCategory.COURSES:
            return ["MCA Syllabus & Labs", "B.Tech Programs", "MCA Faculty Members", "Placement Packages"]
        elif cat == IntentCategory.FACULTY:
            return ["Prof. Rohan Kokate (HOD MCA)", "Prof. Chetan Padole (Project Lead)", "Principal Dr. Shrikant V. Sonekar", "CSE & MBA HODs"]
        elif cat in (IntentCategory.LIBRARY, IntentCategory.HOSTEL, IntentCategory.SPORTS, IntentCategory.FACILITIES):
            return ["TBI Startup Incubation", "High-Performance AI Labs", "College Bus Routes", "Campus Hostels"]
        elif cat == IntentCategory.ATTENDANCE:
            return ["75% Attendance Rule", "MCA Capstone Project", "Anti-Ragging Policy"]
        return ["MCA Course Fees", "Admission Guidelines", "Contact JDCOEM"]
