"""Pydantic Schemas for Administrative Dashboard and Management."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole
from app.schemas.auth import UserResponse


class DashboardStatsResponse(BaseModel):
    """Aggregate statistics for admin dashboard."""

    total_users: int
    total_students: int
    total_admins: int
    total_departments: int
    total_courses: int
    total_faculty: int
    total_conversations: int
    total_messages: int
    database_status: str


class AuditLogResponse(BaseModel):
    """Event log representation."""

    id: int
    user_id: Optional[int] = None
    action: str
    resource: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    """Paginated user listing for administrator view."""

    total: int
    users: List[UserResponse]
