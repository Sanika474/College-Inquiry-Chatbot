"""Central Models Package Exporting All Entities."""

from app.db.base import Base, TimestampMixin
from app.models.user import User, UserRole, UserSession
from app.models.college import (
    CollegeInfo,
    Department,
    Course,
    CourseFee,
    Faculty,
    Facility,
    KnowledgeDocument,
)
from app.models.conversation import Conversation, Message
from app.models.audit import AuditLog
from app.models.knowledge import KBDocument, KBChunk, KBIngestionJob

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "UserSession",
    "CollegeInfo",
    "Department",
    "Course",
    "CourseFee",
    "Faculty",
    "Facility",
    "KnowledgeDocument",
    "Conversation",
    "Message",
    "AuditLog",
    "KBDocument",
    "KBChunk",
    "KBIngestionJob",
]
