"""Tests for Public College Information Endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_college_info():
    """Verify that /api/v1/college/info returns official college details."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/college/info")
        assert response.status_code == 200
        data = response.json()
        assert "JD College" in data["name"]
        assert data["established_year"] == 2008
        assert "DBATU" in data["affiliation"]
        assert "NAAC" in data["accreditation"]


@pytest.mark.asyncio
async def test_get_departments():
    """Verify that /api/v1/college/departments returns academic departments."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/college/departments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5
        codes = [d["code"] for d in data]
        assert "MCA" in codes
        assert "CSE" in codes


@pytest.mark.asyncio
async def test_get_courses_and_filters():
    """Verify /api/v1/college/courses with department and level filters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Unfiltered
        all_courses = await client.get("/api/v1/college/courses")
        assert all_courses.status_code == 200
        assert len(all_courses.json()) >= 5

        # Filtered by level=UG
        ug_courses = await client.get("/api/v1/college/courses?level=UG")
        assert ug_courses.status_code == 200
        for c in ug_courses.json():
            assert c["level"] == "UG"

        # Filtered by department_code=BCA
        bca_courses = await client.get("/api/v1/college/courses?department_code=BCA")
        assert bca_courses.status_code == 200
        assert len(bca_courses.json()) >= 1
        assert "Computer Applications" in bca_courses.json()[0]["name"]


@pytest.mark.asyncio
async def test_get_fees():
    """Verify /api/v1/college/fees returns fee schedules."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/college/fees")
        assert response.status_code == 200
        fees = response.json()
        assert len(fees) >= 5
        # Check that fees have a positive total_fee
        assert all(f["total_fee"] > 0 for f in fees)


@pytest.mark.asyncio
async def test_get_faculty():
    """Verify /api/v1/college/faculty returns faculty list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/college/faculty")
        assert response.status_code == 200
        faculty = response.json()
        names = [f["name"] for f in faculty]
        assert any("Dhote" in n for n in names)
        assert any("Supatkar" in n for n in names)


@pytest.mark.asyncio
async def test_get_facilities():
    """Verify /api/v1/college/facilities returns facilities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/college/facilities")
        assert response.status_code == 200
        facilities = response.json()
        names = [f["name"] for f in facilities]
        assert "Central Library" in names
        assert "Girls' Hostel" in names
