"""
Real authentication endpoints.

Replaces the dev-mode `/auth/login` from the previous build (which issued
a token for any username with no password check — see its docstring,
which explicitly called this out as a placeholder to replace). This is
that replacement: persisted users with hashed passwords, account lockout,
and rotating/revocable refresh tokens.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.session import get_db_session
from backend.schemas.auth import (
    CurrentUser,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    SessionInfo,
    TokenResponse,
    UserPublic,
)
from backend.services.auth_service import auth_service

router = APIRouter()


@router.post("/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db_session)) -> UserPublic:
    user = auth_service.register(db, request.username, request.email, request.password)
    return UserPublic.model_validate(user)


@router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db_session)) -> TokenResponse:
    user = auth_service.authenticate(db, request.username, request.password)
    bundle = auth_service.issue_tokens(db, user, request.remember_me)
    return TokenResponse(
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        expires_in=bundle.expires_in,
        user=UserPublic.model_validate(bundle.user),
    )


@router.post("/auth/guest", response_model=TokenResponse)
def guest(db: Session = Depends(get_db_session)) -> TokenResponse:
    """Public demo sign-in as the shared guest account; 404 unless GUEST_ACCESS_ENABLED."""
    bundle = auth_service.guest_session(db)
    return TokenResponse(
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        expires_in=bundle.expires_in,
        user=UserPublic.model_validate(bundle.user),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, db: Session = Depends(get_db_session)) -> TokenResponse:
    bundle = auth_service.rotate_refresh_token(db, request.refresh_token)
    return TokenResponse(
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        expires_in=bundle.expires_in,
        user=UserPublic.model_validate(bundle.user),
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: LogoutRequest, db: Session = Depends(get_db_session)) -> None:
    auth_service.revoke_refresh_token(db, request.refresh_token)


@router.post("/auth/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    auth_service.revoke_all_sessions(db, current_user.user_id)


@router.get("/auth/sessions", response_model=list[SessionInfo])
def list_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[SessionInfo]:
    sessions = auth_service.list_active_sessions(db, current_user.user_id)
    return [SessionInfo.model_validate(s) for s in sessions]


@router.get("/auth/me", response_model=UserPublic)
def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UserPublic:
    user = auth_service.get_user(db, current_user.user_id)
    return UserPublic.model_validate(user)
