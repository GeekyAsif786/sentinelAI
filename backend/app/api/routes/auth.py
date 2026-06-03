"""
Development-only authentication helpers.

This router is ONLY mounted when APP_ENV=development.  It issues real JWTs
signed with the configured secret key so that the local frontend can call
protected endpoints without a full identity provider integration.

It must never be exposed in production.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.core.security import RoleName, create_access_token
from app.schemas.common import DevTokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-token", response_model=DevTokenResponse)
def issue_dev_token() -> DevTokenResponse:
    """Return a short-lived JWT for the built-in dev analyst account.

    Only available when APP_ENV=development.
    """
    settings = get_settings()
    if settings.app_env != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        email="dev-analyst@example.com",
        roles={RoleName.admin, RoleName.analyst},
        settings=settings,
    )
    return DevTokenResponse(access_token=token, token_type="bearer")
