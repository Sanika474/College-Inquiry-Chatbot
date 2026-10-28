"""Tests for Administrative Dashboard, User Management, and CSV Export."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_admin_dashboard_unauthenticated_fails():
    """Verify that unauthenticated access to admin dashboard returns HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/admin/dashboard")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_dashboard_student_forbidden():
    """Verify that student login attempting admin access returns HTTP 403."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as student
        await client.post(
            "/api/v1/auth/login",
            json={"email": "student@campusiq.edu", "password": "StudentCampusIQ@2025"},
        )
        # Attempt to access dashboard
        response = await client.get("/api/v1/admin/dashboard")
        assert response.status_code == 403
        assert "Administrator privileges required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_dashboard_admin_success():
    """Verify that admin user accesses dashboard and receives real counter statistics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as admin
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@campusiq.edu", "password": "AdminCampusIQ@2025"},
        )
        assert login_resp.status_code == 200

        # Access dashboard
        response = await client.get("/api/v1/admin/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] >= 2
        assert data["total_courses"] >= 5
        assert data["total_departments"] >= 5
        assert data["database_status"] == "healthy"


@pytest.mark.asyncio
async def test_admin_list_users():
    """Verify that admin can retrieve the user directory."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@campusiq.edu", "password": "AdminCampusIQ@2025"},
        )
        response = await client.get("/api/v1/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        emails = [u["email"] for u in data["users"]]
        assert "admin@campusiq.edu" in emails


@pytest.mark.asyncio
async def test_admin_export_users_csv():
    """Verify that CSV export returns streamable CSV with headers and excludes passwords."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@campusiq.edu", "password": "AdminCampusIQ@2025"},
        )
        response = await client.get("/api/v1/admin/export/users")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert 'attachment; filename="campusiq_users.csv"' in response.headers["content-disposition"]
        csv_text = response.text
        assert "User ID,Full Name,Email,Role,Active Status,Verified,Created At" in csv_text
        assert "admin@campusiq.edu" in csv_text
        assert "password" not in csv_text.lower().split("\n")[0]  # No password header
        assert "argon2" not in csv_text.lower()                   # No hashes exported
