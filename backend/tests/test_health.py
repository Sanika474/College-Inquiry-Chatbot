"""Smoke and Health Check Tests for CampusIQ API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root_health():
    """Verify that /health responds with status 200 and expected payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "campusiq-backend"
        assert "version" in data


@pytest.mark.asyncio
async def test_api_v1_health():
    """Verify that /api/v1/health responds with status 200 and environment info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api_version"] == "v1"
        assert "environment" in data
        assert "ai_fallback_enabled" in data
