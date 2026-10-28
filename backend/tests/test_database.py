"""Database Model and Relational Integrity Tests."""

import pytest
from app.core.security import verify_password
from app.db.session import SessionLocal
from app.models import (
    CollegeInfo,
    Course,
    CourseFee,
    Department,
    Facility,
    Faculty,
    KnowledgeDocument,
    User,
    UserRole,
)


@pytest.fixture
def db():
    """Yield a database session for testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_users_exist_with_argon2_passwords(db):
    """Verify seeded users exist and their passwords verify against Argon2id hashes."""
    admin = db.query(User).filter(User.email == "admin@campusiq.edu").first()
    assert admin is not None
    assert admin.role == UserRole.ADMIN
    assert verify_password("AdminCampusIQ@2025", admin.hashed_password) is True

    legacy_admin = db.query(User).filter(User.email == "masss@gmail.com").first()
    assert legacy_admin is not None
    assert legacy_admin.role == UserRole.ADMIN
    assert verify_password("Pappupass", legacy_admin.hashed_password) is True

    student = db.query(User).filter(User.email == "student@campusiq.edu").first()
    assert student is not None
    assert student.role == UserRole.STUDENT
    assert verify_password("StudentCampusIQ@2025", student.hashed_password) is True


def test_college_info_record(db):
    """Verify college institutional information."""
    info = db.query(CollegeInfo).first()
    assert info is not None
    assert "JD College" in info.name
    assert info.established_year == 2008
    assert "DBATU" in info.affiliation


def test_departments_and_courses_relationships(db):
    """Verify departments, courses, and relational integrity."""
    mca_dept = db.query(Department).filter(Department.code == "MCA").first()
    assert mca_dept is not None
    assert "Rohan Kokate" in mca_dept.hod_name

    courses = db.query(Course).all()
    assert len(courses) >= 5

    # Check fee breakdown for MCA
    mca_course = db.query(Course).filter(Course.code == "MCA").first()
    assert mca_course is not None
    fees = db.query(CourseFee).filter(CourseFee.course_id == mca_course.id).all()
    assert len(fees) >= 2


def test_faculty_and_facilities(db):
    """Verify faculty and facilities data."""
    principal = db.query(Faculty).filter(Faculty.name.like("%Sonekar%")).first()
    assert principal is not None
    assert "Principal" in principal.designation

    tbi = db.query(Facility).filter(Facility.name.like("%Technology Business Incubator%")).first()
    assert tbi is not None
    assert "startup" in tbi.description.lower()

    hostel = db.query(Facility).filter(Facility.name.like("%Hostel%")).first()
    assert hostel is not None
