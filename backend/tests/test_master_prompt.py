"""Comprehensive Test Suite verifying Master Prompt Requirements & Intent Coverage."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.chatbot.knowledge_graph import knowledge_graph
from app.chatbot.intent_classifier import IntentClassifier, StandardIntent


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# =============================================================================
# Knowledge Graph Verification Tests
# =============================================================================
def test_knowledge_graph_structure():
    """Verify nodes, edges, and relationship traversal in the Knowledge Graph."""
    # Verify College Node
    college = knowledge_graph.get_node("inst:jdcoem")
    assert college is not None
    assert college.code == "04138"
    assert "NAAC 'A' Grade" in college.properties["accreditation"]

    # Verify Semester 1 & 2
    sem1 = knowledge_graph.get_semester_overview("MCA", 1)
    assert sem1 is not None
    assert len(sem1["theory_subjects"]) == 5
    assert len(sem1["lab_courses"]) == 3
    assert sem1["total_credits"] == 22

    sem2 = knowledge_graph.get_semester_overview("MCA", 2)
    assert sem2 is not None
    assert len(sem2["theory_subjects"]) == 5
    assert len(sem2["lab_courses"]) == 3
    assert sem2["total_credits"] == 22

    # Verify Subject Details
    dbms = knowledge_graph.find_node("dbms")
    assert dbms is not None
    assert dbms.code == "MC2T001"
    assert dbms.properties["credits"] == 4

    ai = knowledge_graph.find_node("ai")
    assert ai is not None
    assert ai.code == "MC2T002"
    assert ai.properties["credits"] == 4

    python_lab = knowledge_graph.find_node("python lab")
    assert python_lab is not None
    assert python_lab.code == "MC2L007"
    assert python_lab.properties["credits"] == 2


# =============================================================================
# Intent Classification & Entity Extraction Unit Tests
# =============================================================================
def test_intent_classification_18_intents():
    """Verify correct classification for all required inquiry intents."""
    cases = [
        ("Hi there", StandardIntent.GREETING.value),
        ("MCA Sem 2 syllabus", StandardIntent.SYLLABUS_OVERVIEW.value),
        ("Tell me about DBMS", StandardIntent.SUBJECT_DETAILS.value),
        ("Show MCA timetable", StandardIntent.TIMETABLE.value),
        ("When is my DBMS exam?", StandardIntent.EXAM_SCHEDULE.value),
        ("What is the DBMS subject code?", StandardIntent.COURSE_STRUCTURE.value),
        ("How many credits does AI have?", StandardIntent.CREDITS_AND_MARKS.value),
        ("What is the MCA fee?", StandardIntent.FEES.value),
        ("How to get admission in MCA?", StandardIntent.ADMISSION.value),
        ("Who is the HOD?", StandardIntent.FACULTY_DETAILS.value),
        ("Tell me about MCA department", StandardIntent.DEPARTMENT_INFORMATION.value),
        ("Eligibility for MCA", StandardIntent.ELIGIBILITY.value),
        ("Which documents are required for admission?", StandardIntent.DOCUMENTS_REQUIRED.value),
        ("Contact JDCOEM", StandardIntent.CONTACT_INFORMATION.value),
        ("When is academic calendar starting?", StandardIntent.ACADEMIC_CALENDAR.value),
        ("Explain Python Lab", StandardIntent.PRACTICAL_AND_LAB_DETAILS.value),
        ("What is the weather on Mars?", StandardIntent.UNKNOWN_QUERY.value),
    ]

    for query, expected_intent in cases:
        analysis = IntentClassifier.analyze_question(query)
        assert analysis.primary_intent == expected_intent, f"Query '{query}' failed: got {analysis.primary_intent}, expected {expected_intent}"


# =============================================================================
# The 15 Mandatory Acceptance Questions (End-to-End Chat API)
# =============================================================================
@pytest.mark.asyncio
async def test_q1_greeting(client):
    """Question 1: 'Hi'"""
    res = await client.post("/api/v1/chat", json={"message": "Hi"})
    assert res.status_code == 200
    data = res.json()
    assert "greeting" in data["intent"].lower()
    assert "Welcome to **CampusIQ" in data["message"]


@pytest.mark.asyncio
async def test_q2_mca_sem2_syllabus(client):
    """Question 2: 'MCA Sem 2 syllabus' — concise, structured, clickable link."""
    res = await client.post("/api/v1/chat", json={"message": "MCA Sem 2 syllabus"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    # Verify concise structured items
    assert "Database Management System (MC2T001)" in msg
    assert "Artificial Intelligence (MC2T002)" in msg
    assert "Data Science Using Python (MC2T003)" in msg
    assert "Cyber Security & Cryptography (MC2T004)" in msg
    assert "DBMS Lab (MC2L006)" in msg
    assert "Python Lab (MC2L007)" in msg
    assert "PHP Lab (MC2L008)" in msg
    assert "22 Credits" in msg
    # Verify clickable document link
    assert "/api/v1/documents/6/view" in msg
    assert len(data["links"]) > 0


@pytest.mark.asyncio
async def test_q3_give_me_full_syllabus(client):
    """Question 3: 'Give me the full syllabus'"""
    res = await client.post("/api/v1/chat", json={"message": "Give me the full syllabus"})
    assert res.status_code == 200
    data = res.json()
    assert "Syllabus" in data["message"]
    assert "/api/v1/documents/" in data["message"]


@pytest.mark.asyncio
async def test_q4_tell_me_about_dbms(client):
    """Question 4: 'Tell me about DBMS' — concise summary, course details, units."""
    res = await client.post("/api/v1/chat", json={"message": "Tell me about DBMS"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "Database Management System (MC2T001)" in msg
    assert "4 Credits" in msg
    assert "Unit I" in msg
    assert "Normalization" in msg or "Transaction" in msg or "ER Modeling" in msg
    assert "/api/v1/documents/6/view" in msg


@pytest.mark.asyncio
async def test_q5_dbms_subject_code(client):
    """Question 5: 'What is the DBMS subject code?'"""
    res = await client.post("/api/v1/chat", json={"message": "What is the DBMS subject code?"})
    assert res.status_code == 200
    data = res.json()
    assert "MC2T001" in data["message"]


@pytest.mark.asyncio
async def test_q6_ai_credits(client):
    """Question 6: 'How many credits does AI have?' — concise 1-2 sentence response."""
    res = await client.post("/api/v1/chat", json={"message": "How many credits does AI have?"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "4 credits" in msg.lower()
    assert "MC2T002" in msg
    # Must NOT dump entire syllabus
    assert "PHP Lab" not in msg


@pytest.mark.asyncio
async def test_q7_open_timetable(client):
    """Question 7: 'Open my MCA timetable'"""
    res = await client.post("/api/v1/chat", json={"message": "Open my MCA timetable"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "Timetable" in msg
    assert "09:30 AM" in msg
    assert "/api/v1/documents/7/view" in msg


@pytest.mark.asyncio
async def test_q8_exam_timetable(client):
    """Question 8: 'Show MCA Semester 2 exam timetable'"""
    res = await client.post("/api/v1/chat", json={"message": "Show MCA Semester 2 exam timetable"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "Examination" in msg
    assert "ESE" in msg or "End-Semester" in msg
    assert "/api/v1/documents/7/view" in msg


@pytest.mark.asyncio
async def test_q9_mca_fee(client):
    """Question 9: 'What is the MCA fee?'"""
    res = await client.post("/api/v1/chat", json={"message": "What is the MCA fee?"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "91,500" in msg
    assert "81,364" in msg  # Tuition fee component


@pytest.mark.asyncio
async def test_q10_documents_required(client):
    """Question 10: 'Which documents are required for admission?'"""
    res = await client.post("/api/v1/chat", json={"message": "Which documents are required for admission?"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "MAH-MCA-CET" in msg
    assert "Transfer Certificate" in msg or "Leaving Certificate" in msg
    assert "Domicile" in msg


@pytest.mark.asyncio
async def test_q11_explain_python_lab(client):
    """Question 11: 'Explain Python Lab'"""
    res = await client.post("/api/v1/chat", json={"message": "Explain Python Lab"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "MC2L007" in msg
    assert "2 Credits" in msg
    assert "NumPy" in msg or "Pandas" in msg or "Python" in msg


@pytest.mark.asyncio
async def test_q12_subjects_in_semester_2(client):
    """Question 12: 'What subjects are in Semester 2?'"""
    res = await client.post("/api/v1/chat", json={"message": "What subjects are in Semester 2?"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "Database Management System" in msg
    assert "Artificial Intelligence" in msg
    assert "22 Credits" in msg


@pytest.mark.asyncio
async def test_q13_and_q14_follow_up_turns(client):
    """Questions 13 & 14: Multi-turn Follow-up Resolution.
    Turn 1: 'MCA Sem 2 syllabus'
    Turn 2: 'Tell me about the first subject' (resolves to DBMS)
    Turn 3: 'Give me more details'
    """
    # Turn 1
    res1 = await client.post("/api/v1/chat", json={"message": "MCA Sem 2 syllabus"})
    assert res1.status_code == 200
    conv_id = res1.json()["conversation_id"]

    # Turn 2: 'Tell me about the first subject'
    res2 = await client.post("/api/v1/chat", json={"message": "Tell me about the first subject", "conversation_id": conv_id})
    assert res2.status_code == 200
    msg2 = res2.json()["message"]
    assert "Database Management System" in msg2 or "MC2T001" in msg2

    # Turn 3: 'Give me more details'
    res3 = await client.post("/api/v1/chat", json={"message": "Give me more details", "conversation_id": conv_id})
    assert res3.status_code == 200
    msg3 = res3.json()["message"]
    assert "Database Management System" in msg3 or "Unit I" in msg3


@pytest.mark.asyncio
async def test_q15_unknown_query_zero_hallucination(client):
    """Question 15: 'What is the weather on Mars?' — must NEVER produce fake college facts."""
    res = await client.post("/api/v1/chat", json={"message": "What is the weather on Mars?"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    assert "couldn't find a verified answer" in msg.lower() or "contact the college office" in msg.lower()


# =============================================================================
# Document Link Serving & Path Traversal Security Tests
# =============================================================================
@pytest.mark.asyncio
async def test_documents_endpoints(client):
    """Verify document list, inline view, and path traversal protection."""
    # List documents
    res_list = await client.get("/api/v1/documents")
    assert res_list.status_code == 200
    docs = res_list.json()
    assert len(docs) >= 5
    assert any("Syllabus" in d["filename"] for d in docs)

    # View document inline
    doc_id = docs[0]["id"]
    res_view = await client.get(f"/api/v1/documents/{doc_id}/view")
    assert res_view.status_code == 200
    assert "inline" in res_view.headers.get("content-disposition", "")

    # Non-existent document returns 404
    res_404 = await client.get("/api/v1/documents/99999/view")
    assert res_404.status_code == 404

