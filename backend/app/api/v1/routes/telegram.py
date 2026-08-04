from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.config import settings
from app.dependencies import get_current_user
from app.dependencies.telegram import get_telegram_service
from app.models.user import User
from app.schemas.telegram import TelegramLinkResponse, TelegramStatusResponse
from app.services.telegram_service import TelegramService

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/link", response_model=TelegramLinkResponse)
async def create_telegram_link(
    current_user: Annotated[User, Depends(get_current_user)],
    telegram_service: Annotated[TelegramService, Depends(get_telegram_service)],
) -> TelegramLinkResponse:
    """docs/57 §3 - issues a short-lived link code the user sends to the
    bot via `/start <code>` to complete linking."""
    account = telegram_service.create_link_code(current_user.id)
    return TelegramLinkResponse(
        link_code=account.link_code,
        bot_username=settings.telegram_bot_username,
        expires_at=account.link_code_expires_at,
    )


@router.get("/status", response_model=TelegramStatusResponse)
async def get_telegram_status(
    current_user: Annotated[User, Depends(get_current_user)],
    telegram_service: Annotated[TelegramService, Depends(get_telegram_service)],
) -> TelegramStatusResponse:
    account = telegram_service.get_account(current_user.id)
    if account is None or account.linked_at is None:
        return TelegramStatusResponse(linked=False)
    return TelegramStatusResponse(linked=True, linked_at=account.linked_at)


@router.delete("/link", status_code=status.HTTP_204_NO_CONTENT)
async def delete_telegram_link(
    current_user: Annotated[User, Depends(get_current_user)],
    telegram_service: Annotated[TelegramService, Depends(get_telegram_service)],
) -> None:
    telegram_service.unlink(current_user.id)
