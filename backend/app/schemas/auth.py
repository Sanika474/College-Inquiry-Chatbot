"""Authentication and User Request/Response Schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    """Schema for user registration."""

    full_name: str = Field(..., min_length=2, max_length=150, description="Full legal or student name")
    email: EmailStr = Field(..., description="Valid college or personal email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password with minimum 8 characters")


class UserLoginRequest(BaseModel):
    """Schema for user authentication."""

    email: EmailStr = Field(..., description="Registered account email")
    password: str = Field(..., min_length=1, description="Account password")


class UserResponse(BaseModel):
    """Safe public user profile representation (excluding password hashes)."""

    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """Schema for administrative user profile updates."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class AuthStatusResponse(BaseModel):
    """Response returned upon checking current authentication status."""

    authenticated: bool
    user: Optional[UserResponse] = None
