"""Authentication and RBAC Endpoint Tests."""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_register_student_success():
    """Verify that a new student can register successfully."""
    transport = ASGITransport(app=app)
    unique_email = f"test_student_{uuid.uuid4().hex[:8]}@campusiq.edu"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "full_name": "Test Student New",
            "email": unique_email,
            "password": "SecurePassword123!",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == unique_email
        assert data["full_name"] == "Test Student New"
        assert data["role"] == "student"
        assert "hashed_password" not in data  # Ensure password hash is never exposed


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected():
    """Verify that duplicate email registration returns HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "full_name": "Duplicate Student",
            "email": "student@campusiq.edu",  # Seeded in Phase 3
            "password": "Password123!",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password_rejected():
    """Verify that passwords under 8 characters fail validation with HTTP 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "full_name": "Short Password",
            "email": "short_pwd@campusiq.edu",
            "password": "short",
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Verify that wrong password returns HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "email": "student@campusiq.edu",
            "password": "WrongPassword123!",
        }
        response = await client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success_and_session_cookie():
    """Verify that valid login sets an HTTP-only session cookie and returns user profile."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "email": "student@campusiq.edu",
            "password": "StudentCampusIQ@2025",
        }
        response = await client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200
        assert "campusiq_session" in response.cookies
        data = response.json()
        assert data["email"] == "student@campusiq.edu"
        assert data["role"] == "student"


@pytest.mark.asyncio
async def test_authenticated_me_and_logout_flow():
    """Verify full auth lifecycle: login -> get /me -> logout -> get /me rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Unauthenticated /me must fail
        unauth_resp = await client.get("/api/v1/auth/me")
        assert unauth_resp.status_code == 401

        # Step 2: Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "student@campusiq.edu", "password": "StudentCampusIQ@2025"},
        )
        assert login_resp.status_code == 200

        # Step 3: Authenticated /me must succeed
        me_resp = await client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "student@campusiq.edu"

        # Step 4: Status endpoint confirms authenticated
        status_resp = await client.get("/api/v1/auth/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["authenticated"] is True

        # Step 5: Logout
        logout_resp = await client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200

        # Step 6: Post-logout /me must fail with 401
        post_logout_resp = await client.get("/api/v1/auth/me")
        assert post_logout_resp.status_code == 401

        # Step 7: Post-logout status returns authenticated: False
        post_logout_status = await client.get("/api/v1/auth/status")
        assert post_logout_status.status_code == 200
        assert post_logout_status.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_legacy_admin_login():
    """Verify that legacy admin credentials (masss@gmail.com / Pappupass) work securely with Argon2id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "masss@gmail.com", "password": "Pappupass"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "masss@gmail.com"
        assert data["role"] == "admin"
