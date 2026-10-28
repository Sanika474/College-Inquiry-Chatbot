"""Pydantic Schemas for College Institutional Information."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CollegeInfoResponse(BaseModel):
    """Institutional identity details."""

    name: str
    established_year: int
    affiliation: str
    accreditation: str
    campus_size: str
    motto: str
    address: str
    contact_email: str
    contact_phone: str
    website: str

    model_config = ConfigDict(from_attributes=True)


class DepartmentResponse(BaseModel):
    """Department public details."""

    id: int
    name: str
    code: str
    hod_name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CourseFeeResponse(BaseModel):
    """Fee schedule breakdown per academic year."""

    id: int
    course_id: int
    academic_year: str
    year_of_study: int
    tuition_fee: float
    development_fee: float
    lab_fee: float
    other_fee: float
    total_fee: float
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CourseResponse(BaseModel):
    """Academic course information."""

    id: int
    department_id: int
    name: str
    code: str
    level: str
    duration_years: int
    eligibility: str
    intake_capacity: Optional[int] = None
    description: Optional[str] = None
    department_name: Optional[str] = None
    fees: Optional[List[CourseFeeResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class FacultyResponse(BaseModel):
    """Faculty member details."""

    id: int
    department_id: int
    name: str
    designation: str
    qualification: str
    experience_years: Optional[int] = None
    specialization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FacilityResponse(BaseModel):
    """Campus infrastructure details."""

    id: int
    name: str
    category: str
    description: str
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentResponse(BaseModel):
    """Policy or knowledge base source document."""

    id: int
    title: str
    category: str
    content: str
    source_reference: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CourseCreateRequest(BaseModel):
    """Schema for adding a new course (Admin only)."""

    department_id: int
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=30)
    level: str = Field("UG", max_length=30)
    duration_years: int = Field(3, ge=1, le=6)
    eligibility: str = Field(..., min_length=5)
    intake_capacity: Optional[int] = Field(60, ge=1)
    description: Optional[str] = None


class CourseFeeCreateRequest(BaseModel):
    """Schema for setting a fee schedule (Admin only)."""

    course_id: int
    academic_year: str = Field(..., max_length=20)
    year_of_study: int = Field(..., ge=1, le=6)
    tuition_fee: float = Field(0.0, ge=0.0)
    development_fee: float = Field(0.0, ge=0.0)
    lab_fee: float = Field(0.0, ge=0.0)
    other_fee: float = Field(0.0, ge=0.0)
    total_fee: float = Field(..., ge=0.0)
    notes: Optional[str] = None
