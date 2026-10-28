"""Authentication and User Profile Endpoints."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.security import (
    create_session_token,
    get_password_hash,
    sign_session_cookie,
    verify_password,
    verify_session_cookie,
)
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User, UserRole, UserSession
from app.schemas.auth import (
    AuthStatusResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
def register_user(
    payload: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new student account with Argon2id password hashing."""
    normalized_email = payload.email.strip().lower()

    # Check for duplicate email
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Create new student record
    hashed_password = get_password_hash(payload.password)
    user = User(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        hashed_password=hashed_password,
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    # Record audit log
    client_ip = request.client.host if request.client else None
    audit = AuditLog(
        user_id=user.id,
        action="user_registered",
        resource="User",
        resource_id=str(user.id),
        details=f"User {user.email} registered",
        ip_address=client_ip,
    )
    db.add(audit)
    db.commit()
    db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=UserResponse,
    summary="Authenticate and receive an HTTP-only session cookie",
)
def login_user(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate credentials and establish a secure, server-tracked session."""
    normalized_email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact administration.",
        )

    # Create persistent session
    token = create_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)

    session_record = UserSession(
        user_id=user.id,
        session_token=token,
        ip_address=client_ip,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session_record)

    # Record login audit
    audit = AuditLog(
        user_id=user.id,
        action="user_login",
        resource="UserSession",
        resource_id=str(user.id),
        details=f"Successful login from IP {client_ip}",
        ip_address=client_ip,
    )
    db.add(audit)
    db.commit()

    # Set cryptographically signed HTTP-only cookie
    signed_cookie = sign_session_cookie(token)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=signed_cookie,
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )

    return user


@router.post(
    "/logout",
    summary="Log out and invalidate the current session",
)
def logout_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Invalidate server-side session and delete the session cookie."""
    signed_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if signed_cookie:
        token = verify_session_cookie(signed_cookie)
        if token:
            db.query(UserSession).filter(UserSession.session_token == token).delete()
            db.commit()

    # Clear cookie
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )

    return {"message": "Logged out successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Retrieve current authenticated user profile",
)
def get_authenticated_profile(
    current_user: User = Depends(get_current_user),
):
    """Return the profile for the currently authenticated session."""
    return current_user


@router.get(
    "/status",
    response_model=AuthStatusResponse,
    summary="Check session status without raising 401",
)
def get_auth_status(
    current_user: User = Depends(get_current_user_optional),
):
    """Return whether the current client holds an active session."""
    if current_user:
        return AuthStatusResponse(authenticated=True, user=UserResponse.model_validate(current_user))
    return AuthStatusResponse(authenticated=False, user=None)
