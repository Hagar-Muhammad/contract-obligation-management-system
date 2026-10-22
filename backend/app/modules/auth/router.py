from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import InvalidTokenError, decode_access_token
from app.modules.auth import service
from app.modules.auth.dependencies import CurrentUser, bearer_scheme, get_current_user
from app.modules.auth.schemas import LoginRequest, MeResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        settings.refresh_cookie_name,
        token,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.refresh_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )


def _refresh_cookie(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.refresh_cookie_name)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with e-mail and password (FR-AUTH-01)",
    responses={401: {"description": "Invalid credentials or inactive account"}},
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    issued = service.login(
        db,
        payload.email,
        payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    _set_refresh_cookie(response, issued.refresh_token, settings)
    return TokenResponse(
        access_token=issued.access_token, expires_in=issued.expires_in, user=MeResponse.from_user(issued.user)
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Get a new access token using the refresh cookie",
    responses={401: {"description": "Missing, invalid, expired or re-used refresh token"}},
)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    issued = service.refresh(db, _refresh_cookie(request, settings))
    _set_refresh_cookie(response, issued.refresh_token, settings)
    return TokenResponse(
        access_token=issued.access_token, expires_in=issued.expires_in, user=MeResponse.from_user(issued.user)
    )


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, summary="End the current session (FR-AUTH-04)"
)
def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    # Works with an expired access token too: the refresh cookie alone identifies the session.
    session_id = None
    if credentials is not None:
        try:
            _, session_id = decode_access_token(credentials.credentials)
        except InvalidTokenError:
            session_id = None
    service.logout(db, session_id=session_id, raw_refresh_token=_refresh_cookie(request, settings))
    _clear_refresh_cookie(response, settings)


@router.get("/me", response_model=MeResponse, summary="The current user, roles and permissions")
def me(current: CurrentUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse.from_user(current.user)
