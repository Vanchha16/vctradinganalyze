from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.config import settings
from app.dependencies import get_authentication_service, get_current_user, get_user_service
from app.exceptions import RegistrationDisabledException
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.authentication_service import AuthenticationService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Phase 8E (docs/59 §9, ADR-119) - public registration is closed by
    default (`settings.allow_public_registration=False`). Accounts are
    admin-provisioned via `AdminUserService` (`POST /admin/users`) or, for
    the very first account, `backend/scripts/create_admin.py`.
    `UserService.register_user` itself is untouched and still reused by
    both this route and `AdminUserService.create_user` - only reachability
    of this specific route changed.
    """
    if not settings.allow_public_registration:
        raise RegistrationDisabledException()

    return user_service.register_user(
        email=payload.email,
        username=payload.username,
        password=payload.password,
        full_name=payload.full_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> TokenResponse:
    _, access_token, refresh_token = auth_service.login(
        payload.email,
        payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    auth_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> TokenResponse:
    access_token = auth_service.refresh(payload.refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    auth_service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> None:
    auth_service.logout(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
