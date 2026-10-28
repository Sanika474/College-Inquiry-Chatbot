"""College Institutional Information ORM Models."""

from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class CollegeInfo(Base, TimestampMixin):
    """Institutional identity details."""

    __tablename__ = "college_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    established_year: Mapped[int] = mapped_column(Integer, nullable=False)
    affiliation: Mapped[str] = mapped_column(String(200), nullable=False)
    accreditation: Mapped[str] = mapped_column(String(255), nullable=False)
    campus_size: Mapped[str] = mapped_column(String(100), nullable=False)
    motto: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    contact_email: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    website: Mapped[str] = mapped_column(String(150), nullable=False)


class Department(Base, TimestampMixin):
    """Academic departments (e.g. BCA, Computer Science, Chemistry)."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    hod_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    courses: Mapped[List["Course"]] = relationship("Course", back_populates="department", cascade="all, delete-orphan")
    faculty_members: Mapped[List["Faculty"]] = relationship("Faculty", back_populates="department", cascade="all, delete-orphan")


class Course(Base, TimestampMixin):
    """Academic programs offered (e.g., BCA, B.Sc., M.Sc.)."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False)  # UG, PG, PhD, Diploma
    duration_years: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    eligibility: Mapped[str] = mapped_column(Text, nullable=False)
    intake_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="courses")
    fees: Mapped[List["CourseFee"]] = relationship("CourseFee", back_populates="course", cascade="all, delete-orphan")


class CourseFee(Base, TimestampMixin):
    """Verified fee breakdown per academic year and year of study."""

    __tablename__ = "course_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "2024-25"
    year_of_study: Mapped[int] = mapped_column(Integer, nullable=False)    # 1, 2, or 3
    tuition_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    development_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    lab_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    other_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    total_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="fees")


class Faculty(Base, TimestampMixin):
    """Teaching faculty member information."""

    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    qualification: Mapped[str] = mapped_column(String(150), nullable=False)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    specialization: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="faculty_members")


class Facility(Base, TimestampMixin):
    """Campus infrastructure, labs, sports, and hostels."""

    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # Library, Sports, Hostel, Lab, Canteen
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class KnowledgeDocument(Base, TimestampMixin):
    """Institutional policy, admission rules, and general inquiry documents."""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # admission, attendance, general, ncc_nss
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
