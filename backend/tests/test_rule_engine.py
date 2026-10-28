"""Unit Tests for RuleEngine Classification and Intent Priority Resolution."""

import pytest
from app.chatbot.intent_catalog import IntentCategory
from app.chatbot.rule_engine import RuleEngine


@pytest.fixture
def engine():
    return RuleEngine()


def test_text_normalization(engine):
    """Verify acronym stripping and whitespace normalization."""
    assert engine.normalize_text("B.C.A.") == "bca"
    assert engine.normalize_text("  What is B.Sc. (Computer Science)?  ") == "what is bsc computer science"
    assert engine.normalize_text("M.Sc.  Part-I fees!!!") == "msc part i fees"


def test_greeting_intents(engine):
    """Verify greetings classify correctly."""
    for phrase in ["Hello", "Hi there", "hey!", "Good morning", "namaste"]:
        result = engine.classify(phrase)
        assert result.category == IntentCategory.GREETING.value, f"Failed on '{phrase}'"
        assert result.confidence >= 0.90


def test_farewell_intents(engine):
    """Verify farewells and gratitude."""
    for phrase in ["bye", "goodbye", "thank you", "thanks for help"]:
        result = engine.classify(phrase)
        assert result.category == IntentCategory.FAREWELL.value, f"Failed on '{phrase}'"


def test_priority_resolution_course_fees(engine):
    """Verify specific course fee intent (P90) beats generic fees (P50) and generic course (P80)."""
    # MCA fee query
    res_mca = engine.classify("What is the fee for MCA course?")
    assert res_mca.intent_id == "fees_mca"
    assert res_mca.target_entity == "MCA"
    assert res_mca.category == IntentCategory.COURSE_FEES.value
    assert res_mca.confidence >= 0.90

    # B.Tech fee query
    res_btech = engine.classify("tell me btech fees")
    assert res_btech.intent_id == "fees_btech"
    assert res_btech.target_entity == "BTECH_CSE"

    # MBA fee query
    res_mba = engine.classify("how much is mba fee")
    assert res_mba.intent_id == "fees_mba"
    assert res_mba.target_entity == "MBA"


def test_ambiguity_detection(engine):
    """Verify vague single-word fee query triggers clarification."""
    result = engine.classify("fees")
    assert result.is_ambiguous is True
    assert result.clarification_prompt is not None
    assert len(result.suggestions) > 0


def test_faculty_classification(engine):
    """Verify faculty inquiries resolve correctly."""
    res_principal = engine.classify("Who is the principal of the college?")
    assert res_principal.intent_id == "faculty_principal"
    assert res_principal.target_entity == "Dr. Shrikant V. Sonekar"

    res_mca_fac = engine.classify("Who teaches in MCA department?")
    assert res_mca_fac.intent_id == "faculty_mca"
    assert res_mca_fac.target_entity == "MCA Faculty"


def test_facilities_classification(engine):
    """Verify campus facility rules."""
    res_lib = engine.classify("What are the library timings and rules?")
    assert res_lib.intent_id == "facility_library"
    assert res_lib.category == IntentCategory.LIBRARY.value

    res_hostel = engine.classify("Is there a hostel for girls and what is the rent?")
    assert res_hostel.intent_id == "facility_hostel"
    assert res_hostel.category == IntentCategory.HOSTEL.value

    res_sports = engine.classify("What sports facilities and gymnasium are available?")
    assert res_sports.intent_id == "facility_sports"


def test_institutional_policies(engine):
    """Verify policy queries."""
    res_att = engine.classify("Is 75% attendance compulsory?")
    assert res_att.intent_id == "policy_attendance"
    assert res_att.category == IntentCategory.ATTENDANCE.value

    res_ragging = engine.classify("What is the anti ragging policy?")
    assert res_ragging.intent_id == "policy_ragging"


def test_unknown_inquiry_fallback(engine):
    """Verify unmapped or out-of-scope inquiries return unknown with confidence 0.0."""
    result = engine.classify("How do astronauts repair telescopes in outer orbit?")
    assert result.intent_id == "unknown"
    assert result.confidence == 0.0
    assert len(result.suggestions) > 0
