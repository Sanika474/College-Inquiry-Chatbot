"""API Request Dependencies: Session Extraction and RBAC."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_session_cookie
from app.db.session import get_db
from app.models.user import User, UserRole, UserSession


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Extract authenticated user from signed session cookie if present and valid."""
    signed_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not signed_cookie:
        return None

    # Verify signature and expiration
    session_token = verify_session_cookie(signed_cookie)
    if not session_token:
        return None

    # Query active session from database
    now = datetime.now(timezone.utc)
    user_session = (
        db.query(UserSession)
        .filter(
            UserSession.session_token == session_token,
            UserSession.expires_at > now,
        )
        .first()
    )

    if not user_session:
        return None

    # Load associated user
    user = db.query(User).filter(User.id == user_session.user_id, User.is_active == True).first()
    return user


def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Enforce authentication on protected endpoints."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforce administrator permissions on privileged endpoints."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required.",
        )
    return current_user
