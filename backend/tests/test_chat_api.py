"""Integration Tests for CampusIQ Chatbot REST Endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_chat_greeting_turn():
    """Verify greeting message initiates a conversation session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"message": "Hello CampusIQ"}
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] > 0
        assert data["intent"] == "greeting"
        assert data["engine"] == "rule_based"
        assert "Welcome to **CampusIQ" in data["message"]
        assert len(data["suggestions"]) > 0


@pytest.mark.asyncio
async def test_chat_multi_turn_course_fee():
    """Verify multi-turn inquiry using existing conversation_id for MCA fee lookup."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Turn 1: Greeting
        res1 = await client.post("/api/v1/chat", json={"message": "Hi"})
        assert res1.status_code == 200
        conv_id = res1.json()["conversation_id"]

        # Turn 2: MCA Fee Query
        res2 = await client.post(
            "/api/v1/chat",
            json={"message": "What is the fee for MCA?", "conversation_id": conv_id},
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["conversation_id"] == conv_id
        assert data2["intent"] == "fees_mca"
        assert "91,500" in data2["message"]  # Seeded MCA Year 1 fee
        assert "Official Fee Ledger" in data2["sources"][0]


@pytest.mark.asyncio
async def test_chat_ambiguity_clarification():
    """Verify vague query returns clarification prompt."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json={"message": "fees"})
        assert response.status_code == 200
        data = response.json()
        assert data["engine"] == "clarification"
        assert "Which course fee" in data["message"]
        assert "MCA Fees" in data["suggestions"]


@pytest.mark.asyncio
async def test_chat_attendance_policy_query():
    """Verify institutional attendance regulation lookup."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json={"message": "What is the attendance policy?"})
        assert response.status_code == 200
        data = response.json()
        assert "75%" in data["message"]
        assert data["intent"] == "policy_attendance"


@pytest.mark.asyncio
async def test_chat_unknown_query_fallback():
    """Verify out-of-domain query returns graceful fallback."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json={"message": "How do deep sea submarine reactors work?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "unknown"
        assert "couldn't locate specific information" in data["message"]


@pytest.mark.asyncio
async def test_conversations_listing_and_history():
    """Verify listing conversation history and deleting sessions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a conversation
        post_res = await client.post("/api/v1/chat", json={"message": "Tell me about Central Library"})
        assert post_res.status_code == 200
        conv_id = post_res.json()["conversation_id"]

        # List conversations
        list_res = await client.get("/api/v1/chat/conversations")
        assert list_res.status_code == 200
        conv_list = list_res.json()
        assert any(c["id"] == conv_id for c in conv_list)

        # Get conversation details
        detail_res = await client.get(f"/api/v1/chat/conversations/{conv_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == conv_id
        assert len(detail["messages"]) >= 2  # User message + bot message

        # Delete conversation
        del_res = await client.delete(f"/api/v1/chat/conversations/{conv_id}")
        assert del_res.status_code == 204

        # Verify 404 after deletion
        check_res = await client.get(f"/api/v1/chat/conversations/{conv_id}")
        assert check_res.status_code == 404
