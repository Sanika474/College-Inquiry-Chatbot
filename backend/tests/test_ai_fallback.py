"""Unit and Integration Tests for AI Fallback Provider and Orchestration."""

from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.chatbot.ai_provider import AIProvider
from app.chatbot.orchestrator import ChatOrchestrator
from app.db.session import SessionLocal


def test_ai_provider_offline_when_unconfigured():
    """Verify that AIProvider is safely disabled when API keys are not supplied."""
    provider = AIProvider(provider=None, api_key=None)
    assert provider.is_available() is False
    assert provider.generate_response("Explain quantum computing") is None


def test_ai_provider_gemini_success(monkeypatch):
    """Verify Google Gemini REST response parsing and source labeling."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "JDCOEM provides advanced cloud computing labs and AI incubation for MCA students."
                        }
                    ]
                }
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

    provider = AIProvider(provider="gemini", api_key="mock_gemini_key", model_name="gemini-1.5-flash")
    assert provider.is_available() is True

    result = provider.generate_response("What computing facilities are available?")
    assert result is not None
    assert "cloud computing labs" in result["text"]
    assert "Google Gemini" in result["source"]


def test_ai_provider_timeout_graceful_handling(monkeypatch):
    """Verify that network timeout degrades safely to None without crashing."""
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.TimeoutException("Network timed out")
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_client)

    provider = AIProvider(provider="gemini", api_key="mock_gemini_key")
    result = provider.generate_response("Tell me about future campus developments")
    assert result is None


def test_orchestrator_routes_to_ai_when_available():
    """Verify that ChatOrchestrator routes unknown queries to AIProvider when available."""
    mock_ai = MagicMock(spec=AIProvider)
    mock_ai.generate_response.return_value = {
        "text": "JDCOEM's MCA students can publish research papers in collaboration with faculty mentors.",
        "source": "Mocked Grounded AI Provider",
    }

    orchestrator = ChatOrchestrator(ai_provider=mock_ai)
    db = SessionLocal()
    try:
        res = orchestrator.process_message(
            db=db,
            user_message="What was the primary philosophy of Renaissance architecture in Elizabethan England?",
        )
        assert res["engine"] == "ai_fallback"
        assert "research papers" in res["message"]
        assert "Mocked Grounded AI Provider" in res["sources"][0]
        assert "MCA Course Details" in res["suggestions"]
    finally:
        db.close()


def test_orchestrator_falls_back_when_ai_offline():
    """Verify that ChatOrchestrator gracefully defaults to rule-based fallback when AI is unavailable."""
    offline_ai = AIProvider(api_key=None)
    orchestrator = ChatOrchestrator(ai_provider=offline_ai)
    db = SessionLocal()
    try:
        res = orchestrator.process_message(
            db=db,
            user_message="Explain quantum entanglement in orbital satellites",
        )
        assert res["engine"] == "rule_based"
        assert "couldn't locate specific information" in res["message"]
        assert "JDCOEM" in res["message"]
        assert "JDCOEM Information Helpdesk" in res["sources"][0]
    finally:
        db.close()
