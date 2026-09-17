"""`GET /admin/performance` (ADR-174). Mirrors `admin_logs.py`'s
structure - flat route module, `require_admin`-gated.

Read-only by design and GET-only by design: this endpoint answers "did
the stored signals work", and nothing here may create, update or delete
anything. `SignalPerformanceService` has no mutating method either.

Deliberately not part of `GET /admin/analytics` (ADR-174): that endpoint
answers "who is using this", this one answers "does it work", and merging
them would couple a user-activity response to trade outcomes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.admin import get_signal_performance_service
from app.dependencies.rbac import require_admin
from app.models.user import User
from app.schemas.admin_performance import AdminPerformanceResponse
from app.services.signal_performance_service import SignalPerformanceService

router = APIRouter(prefix="/admin/performance", tags=["admin"])


@router.get("", response_model=AdminPerformanceResponse)
async def get_signal_performance(
    actor: Annotated[User, Depends(require_admin)],
    service: Annotated[SignalPerformanceService, Depends(get_signal_performance_service)],
) -> AdminPerformanceResponse:
    """Outcomes of every signal created since `settings.signal_metrics_epoch`.

    No query parameters: the epoch is the window, and it is a setting
    rather than a caller-supplied date precisely so two readers cannot
    quote different numbers at each other.
    """
    return service.get_performance()
