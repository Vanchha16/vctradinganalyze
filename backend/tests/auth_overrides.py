"""Test authentication for the read-only analysis routers (ADR-159).

Those routers gate on `get_current_user` and never read the user - they
serve market analysis, not per-user data. So an unpersisted stub is
enough, and using one keeps these tests independent of the users table.

Kept as a helper rather than repeated in nine `client` fixtures so there
is one place to change if the gate ever moves.
"""

from app.dependencies.auth import get_current_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User


def override_authenticated_user(role: UserRole = UserRole.REGISTERED) -> User:
    """Register the override and return the stub, so a test that needs to
    assert on the actor can."""
    user = User(
        email="route-test@example.com",
        username="routetest",
        password_hash="x",
        role=role,
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    return user
