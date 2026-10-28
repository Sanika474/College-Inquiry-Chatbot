"""Administrative Endpoints for Monitoring, User Management, and CRUD Operations."""

import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.college import (
    Course,
    CourseFee,
    Department,
    Faculty,
)
from app.models.conversation import Conversation, Message
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminUserListResponse,
    AuditLogResponse,
    DashboardStatsResponse,
)
from app.schemas.auth import UserResponse, UserUpdateRequest
from app.schemas.college import (
    CourseCreateRequest,
    CourseFeeCreateRequest,
    CourseFeeResponse,
    CourseResponse,
)

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get(
    "/dashboard",
    response_model=DashboardStatsResponse,
    summary="Get aggregate system metrics and counters",
)
def get_dashboard_metrics(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve verified database counters for the admin dashboard."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_students = db.query(func.count(User.id)).filter(User.role == UserRole.STUDENT).scalar() or 0
    total_admins = db.query(func.count(User.id)).filter(User.role == UserRole.ADMIN).scalar() or 0
    total_departments = db.query(func.count(Department.id)).scalar() or 0
    total_courses = db.query(func.count(Course.id)).scalar() or 0
    total_faculty = db.query(func.count(Faculty.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0

    return DashboardStatsResponse(
        total_users=total_users,
        total_students=total_students,
        total_admins=total_admins,
        total_departments=total_departments,
        total_courses=total_courses,
        total_faculty=total_faculty,
        total_conversations=total_conversations,
        total_messages=total_messages,
        database_status="healthy",
    )


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List registered users with pagination",
)
def list_users(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve registered accounts with safe metadata (no password hashes)."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)

    total = query.count()
    users = query.order_by(User.id.desc()).offset(skip).limit(limit).all()

    return AdminUserListResponse(
        total=total,
        users=[UserResponse.model_validate(u) for u in users],
    )


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user status or role",
)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update active status, name, or role for a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )

    # Prevent admin from deactivating themselves
    if user.id == admin_user.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account.",
        )

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    # Audit log
    audit = AuditLog(
        user_id=admin_user.id,
        action="admin_updated_user",
        resource="User",
        resource_id=str(user.id),
        details=f"Admin {admin_user.email} updated user {user.email}",
    )
    db.add(audit)
    db.commit()
    db.refresh(user)

    return user


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="Review recent security and audit logs",
)
def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve system event logs."""
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()


@router.get(
    "/export/users",
    summary="Export authorized user directory to CSV",
)
def export_users_csv(
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Stream a compliant CSV export of user accounts (strictly excludes passwords)."""
    users = db.query(User).order_by(User.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID", "Full Name", "Email", "Role", "Active Status", "Verified", "Created At"])

    for u in users:
        writer.writerow([
            u.id,
            u.full_name,
            u.email,
            u.role.value,
            "Active" if u.is_active else "Inactive",
            "Yes" if u.is_verified else "No",
            u.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        ])

    output.seek(0)

    # Log export event
    audit = AuditLog(
        user_id=admin_user.id,
        action="admin_exported_users_csv",
        resource="User",
        details=f"Admin {admin_user.email} exported {len(users)} user records",
    )
    db.add(audit)
    db.commit()

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="campusiq_users.csv"'},
    )


@router.post(
    "/courses",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new academic course",
)
def create_course(
    payload: CourseCreateRequest,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new course offering under an established department."""
    dept = db.query(Department).filter(Department.id == payload.department_id).first()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with ID {payload.department_id} does not exist.",
        )

    existing = db.query(Course).filter(Course.code == payload.code.strip().upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course with code '{payload.code}' already exists.",
        )

    course = Course(
        department_id=payload.department_id,
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        level=payload.level.strip().upper(),
        duration_years=payload.duration_years,
        eligibility=payload.eligibility.strip(),
        intake_capacity=payload.intake_capacity,
        description=payload.description,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    res = CourseResponse.model_validate(course)
    res.department_name = dept.name
    return res


@router.post(
    "/fees",
    response_model=CourseFeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a verified fee schedule",
)
def create_course_fee(
    payload: CourseFeeCreateRequest,
    admin_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Add a verified fee schedule entry for a course and year of study."""
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {payload.course_id} does not exist.",
        )

    fee = CourseFee(
        course_id=payload.course_id,
        academic_year=payload.academic_year.strip(),
        year_of_study=payload.year_of_study,
        tuition_fee=payload.tuition_fee,
        development_fee=payload.development_fee,
        lab_fee=payload.lab_fee,
        other_fee=payload.other_fee,
        total_fee=payload.total_fee,
        notes=payload.notes,
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)

    return fee
