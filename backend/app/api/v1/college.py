"""Public Endpoints for College Information, Courses, Fees, and Faculty."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.college import (
    CollegeInfo,
    Course,
    CourseFee,
    Department,
    Facility,
    Faculty,
    KnowledgeDocument,
)
from app.schemas.college import (
    CollegeInfoResponse,
    CourseFeeResponse,
    CourseResponse,
    DepartmentResponse,
    FacilityResponse,
    FacultyResponse,
    KnowledgeDocumentResponse,
)

router = APIRouter(prefix="/college", tags=["College Information"])


@router.get("/info", response_model=CollegeInfoResponse, summary="Get institutional identity details")
def get_college_info(db: Session = Depends(get_db)):
    """Retrieve official college background, accreditations, and contact information."""
    info = db.query(CollegeInfo).first()
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College information record has not been initialized.",
        )
    return info


@router.get("/departments", response_model=List[DepartmentResponse], summary="List academic departments")
def get_departments(db: Session = Depends(get_db)):
    """Retrieve all academic departments with their respective HODs."""
    return db.query(Department).order_by(Department.name).all()


@router.get("/courses", response_model=List[CourseResponse], summary="List all academic courses")
def get_courses(
    department_code: Optional[str] = Query(None, description="Filter by department code (e.g. BCA, CS)"),
    level: Optional[str] = Query(None, description="Filter by level (UG, PG, PhD)"),
    db: Session = Depends(get_db),
):
    """Retrieve academic programs with duration and eligibility criteria."""
    query = db.query(Course).join(Department).options(joinedload(Course.department))
    if department_code:
        query = query.filter(Department.code == department_code.strip().upper())
    if level:
        query = query.filter(Course.level == level.strip().upper())

    courses = query.order_by(Course.level.desc(), Course.name).all()
    # Populate department_name
    results = []
    for c in courses:
        res = CourseResponse.model_validate(c)
        res.department_name = c.department.name if c.department else None
        results.append(res)
    return results


@router.get("/courses/{course_id}", response_model=CourseResponse, summary="Get course details with fees")
def get_course_detail(course_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed information and fee schedule for a specific course."""
    course = (
        db.query(Course)
        .options(joinedload(Course.department), joinedload(Course.fees))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} does not exist.",
        )
    res = CourseResponse.model_validate(course)
    res.department_name = course.department.name if course.department else None
    return res


@router.get("/fees", response_model=List[CourseFeeResponse], summary="Query verified course fee schedules")
def get_course_fees(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    academic_year: Optional[str] = Query(None, description="Filter by academic year (e.g. 2024-25)"),
    db: Session = Depends(get_db),
):
    """Retrieve verified fee breakdowns across courses and years of study."""
    query = db.query(CourseFee)
    if course_id:
        query = query.filter(CourseFee.course_id == course_id)
    if academic_year:
        query = query.filter(CourseFee.academic_year == academic_year.strip())

    return query.order_by(CourseFee.course_id, CourseFee.year_of_study).all()


@router.get("/faculty", response_model=List[FacultyResponse], summary="List faculty members")
def get_faculty(
    department_code: Optional[str] = Query(None, description="Filter by department code"),
    db: Session = Depends(get_db),
):
    """Retrieve faculty profiles, qualifications, and department associations."""
    query = db.query(Faculty).join(Department).options(joinedload(Faculty.department))
    if department_code:
        query = query.filter(Department.code == department_code.strip().upper())

    faculty_list = query.order_by(Faculty.department_id, Faculty.name).all()
    results = []
    for f in faculty_list:
        res = FacultyResponse.model_validate(f)
        res.department_name = f.department.name if f.department else None
        results.append(res)
    return results


@router.get("/facilities", response_model=List[FacilityResponse], summary="List campus facilities")
def get_facilities(
    category: Optional[str] = Query(None, description="Filter by category (Library, Hostel, Sports, Laboratory)"),
    db: Session = Depends(get_db),
):
    """Retrieve campus infrastructure facilities."""
    query = db.query(Facility)
    if category:
        query = query.filter(Facility.category.ilike(f"%{category.strip()}%"))
    return query.order_by(Facility.name).all()


@router.get("/documents", response_model=List[KnowledgeDocumentResponse], summary="List institutional knowledge documents")
def get_knowledge_documents(
    category: Optional[str] = Query(None, description="Filter by category (attendance, admission, general, ncc_nss)"),
    db: Session = Depends(get_db),
):
    """Retrieve institutional policies and rule guidelines."""
    query = db.query(KnowledgeDocument)
    if category:
        query = query.filter(KnowledgeDocument.category == category.strip().lower())
    return query.order_by(KnowledgeDocument.id).all()
